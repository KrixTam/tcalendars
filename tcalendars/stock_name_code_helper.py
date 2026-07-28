import re
import sys
import select
from pypinyin import pinyin, Style
from os import path
import pandas as pd
from moment import moment
import akshare as ak
from tcalendars.tools.yfinance_query import search_yahoo_finance
from tcalendars.singleton import Singleton
from tcalendars.db import DatabaseManager

CWD = path.abspath(path.dirname(__file__))

def _interactive_input_with_timeout(prompt: str, timeout: int = 30) -> str: # pragma: no cover
    """
    带超时的交互式输入。
    如果环境不支持或超时，则返回空字符串。
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        return sys.stdin.readline().strip()
    print("\n[Timeout] 自动跳过交互输入。")
    return ""

def _generate_pinyin(name) -> str:
    """
    生成拼音首字母（全部大写），忽略非中文字符。
    """
    if pd.isna(name) or name is None:
        return ""
    name_str = str(name).strip()
    if not name_str or name_str.lower() in ('nan', 'none'):
        return ""
    py_list = pinyin(name_str, style=Style.FIRST_LETTER, strict=False)
    # 将列表展平并拼接
    result = "".join([item[0] for item in py_list if item])
    return result.upper()

def _generate_full_pinyin(text) -> str:
    """
    生成完整拼音（不含空格），用于中文近似匹配排序。
    """
    if pd.isna(text) or text is None:
        return ""
    text_str = str(text).strip()
    if not text_str or text_str.lower() in ('nan', 'none'):
        return ""
    py_list = pinyin(text_str, style=Style.NORMAL, strict=False)
    return "".join([item[0] for item in py_list if item]).lower()


PINYIN_CONFUSION_GROUPS = (
    ("B", "P"),
    ("D", "T"),
    ("G", "K"),
    ("J", "Q", "X"),
    ("N", "L"),
    ("F", "H"),
    ("R", "L"),
    ("N", "L"),
    ("S", "Z"),
)

PINYIN_CONFUSION_MAP = {
    letter: tuple(sorted({alt for group in PINYIN_CONFUSION_GROUPS if letter in group for alt in group if alt != letter}))
    for group in PINYIN_CONFUSION_GROUPS
    for letter in group
}


class StockNameCodeHelper(metaclass=Singleton):
    def __init__(self):
        self._db = DatabaseManager(CWD)
        self._stock_name_code = pd.DataFrame(columns=['code', 'name', 'market', 'pinyin'])
        self.update_stock_name_code()

    def _clean_and_generate_pinyin(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理前缀清洗，并生成拼音首字母。
        """
        if df.empty:
            df = df.copy()
            if 'pinyin' not in df.columns:
                df['pinyin'] = pd.Series(dtype='object')
            return df

        # 加载旧数据以便回退
        old_df = self._db.read_dataframe('stock_name_code')
        old_dict = dict(zip(old_df['code'], old_df['name'])) if not old_df.empty else {}

        def process_row(row):
            code = str(row['code'])
            original_name = row['name']
            
            # 处理 NaN / None 等情况
            if pd.isna(original_name) or original_name is None:
                clean_name = ""
            else:
                original_name = str(original_name).strip()
                if original_name.lower() in ('nan', 'none'):
                    clean_name = ""
                else:
                    clean_name = original_name

                    # 匹配分红前缀 (XD, XR, DR)
                    if re.match(r'^(XD|XR|DR)', original_name, re.IGNORECASE):
                        # 尝试从旧数据中找回原名
                        if code in old_dict:
                            clean_name = old_dict[code]
                        else:
                            clean_name = re.sub(r'^(XD|XR|DR)', '', original_name, flags=re.IGNORECASE)
                    
                    # 匹配新股前缀 (N, C)
                    elif re.match(r'^[NC]', original_name, re.IGNORECASE):
                        if code in old_dict:
                            clean_name = old_dict[code]
                        else:
                            # 交互式询问真实名称
                            prompt = f"检测到新股/次新股简称 '{original_name}' (代码: {code})。请输入真实简称 (等待30秒超时将自动截断): "
                            user_input = _interactive_input_with_timeout(prompt, 30)
                            if user_input:
                                clean_name = user_input
                            else:
                                clean_name = re.sub(r'^[NC]', '', original_name, flags=re.IGNORECASE)

            return pd.Series({
                'name': clean_name if clean_name else None,
                'pinyin': _generate_pinyin(clean_name)
            })

        # 应用清洗和拼音生成逻辑
        processed = df.apply(process_row, axis=1)
        df['name'] = processed['name']
        df['pinyin'] = processed['pinyin']
        return df

    def update_stock_name_code(self):
        '''
        更新股票名称代码表
        '''
        update_flag = False
        last_update = self._db.get_last_update('stock_name_code')
        today = moment().format('YYYY-MM-DD')
        
        if last_update:
            if last_update < today:
                update_flag = True
        else:
            update_flag = True
            
        if update_flag:
            try:
                # 1. 获取沪市+深市+北交所股票列表（akshare最新接口）
                # 沪市A股
                df_sh = ak.stock_info_sh_name_code("主板A股")
                df_sh = df_sh.rename(columns={"证券代码": "code", "证券简称": "name"})
                df_sh["market"] = "沪市"

                # 沪市科创板
                df_kc = ak.stock_info_sh_name_code("科创板")
                df_kc = df_kc.rename(columns={"证券代码": "code", "证券简称": "name"})
                df_kc["market"] = "沪市"
                
                # 深市A股（包含创业板）
                df_sz = ak.stock_info_sz_name_code()
                df_sz = df_sz.rename(columns={"A股代码": "code", "A股简称": "name"})
                df_sz["market"] = "深市"
                
                # 北交所A股
                df_bj = ak.stock_info_bj_name_code()
                df_bj = df_bj.rename(columns={"证券代码": "code", "证券简称": "name"})
                df_bj["market"] = "北交所"
                
                # 合并所有市场，去重，补全6位代码（避免短码）
                df_all = pd.concat([df_sh[["code", "name", "market"]], 
                                    df_kc[["code", "name", "market"]],
                                    df_sz[["code", "name", "market"]], 
                                    df_bj[["code", "name", "market"]]], ignore_index=True)
                df_all["code"] = df_all["code"].astype(str).str.zfill(6)  # 补全6位（如547→000547）
                df_all = df_all.drop_duplicates(subset=["code"], keep="first")  # 去重
                
                # 处理前缀清洗和拼音生成
                df_all = self._clean_and_generate_pinyin(df_all)
                
                # 2. 保存到DB
                self._db.save_dataframe('stock_name_code', df_all)
                self._db.set_last_update('stock_name_code', today)
                
                self._stock_name_code = df_all
                print(f"更新股票名称代码表成功，共{len(df_all)}条记录")
            except Exception as e:
                print(f"更新股票名称代码表失败：{e}")
                # 尝试加载旧数据
                self._stock_name_code = self._db.read_dataframe('stock_name_code')
        else:  # pragma: no cover
            print(f"股票名称代码表已最新，无需更新")
            self._stock_name_code = self._db.read_dataframe('stock_name_code')

    def get_stock_name(self, code: str):
        '''
        获取股票代码对应的股票名称
        '''
        try:
            res = self._stock_name_code.loc[self._stock_name_code['code'] == code].iloc[0]['name']
        except IndexError:
            res = None
        return res

    def get_stock_code(self, name: str):
        '''
        获取股票名称对应的股票代码
        '''
        try:
            res = self._stock_name_code.loc[self._stock_name_code['name'] == name].iloc[0]['code']
        except IndexError:
            res = None
        return res

    def query(self, keyword: str, limit: int = 5) -> list:
        '''
        智能综合查询（支持代码、汉字、拼音首字母）
        返回最可能的结果列表，格式为 list[dict]
        '''
        if not keyword or pd.isna(keyword):
            return []
            
        keyword_str = str(keyword).strip()
        if not keyword_str:
            return []
        if len(keyword_str) == 1:
            return []

        # 仅接受 6 位数字或 ? 组成的代码查询；其他长度直接拒绝。
        if all(ch.isdigit() or ch == '?' for ch in keyword_str) and len(keyword_str) != 6:
            return []

        keyword_upper = keyword_str.upper()
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in keyword_str)
        is_code_pattern = len(keyword_str) == 6 and all(ch.isdigit() or ch == '?' for ch in keyword_str)
        converted_pinyin = _generate_pinyin(keyword_str) if has_chinese else ""

        def _as_text(value) -> str:
            if pd.isna(value) or value is None:
                return ""
            return str(value).strip()

        def _common_prefix_len(left: str, right: str) -> int:
            count = 0
            for lch, rch in zip(left, right):
                if lch != rch:
                    break
                count += 1
            return count

        def _common_suffix_len(left: str, right: str) -> int:
            return _common_prefix_len(left[::-1], right[::-1])

        def _char_distance(left: str, right: str):
            if len(left) != len(right):
                return None
            return sum(lch != rch for lch, rch in zip(left, right))

        def _edit_distance(left: str, right: str) -> int:
            if left == right:
                return 0
            if not left:
                return len(right)
            if not right:
                return len(left)

            prev = list(range(len(right) + 1))
            for i, lch in enumerate(left, start=1):
                curr = [i]
                for j, rch in enumerate(right, start=1):
                    curr.append(min(
                        prev[j] + 1,
                        curr[j - 1] + 1,
                        prev[j - 1] + (0 if lch == rch else 1)
                    ))
                prev = curr
            return prev[-1]

        def _append_candidate(container: list, row, score: int, tie_breakers: tuple):
            container.append({
                'code': _as_text(row['code']),
                'name': _as_text(row['name']),
                'market': _as_text(row['market']),
                'pinyin': _as_text(row['pinyin']),
                '_score': score,
                '_tie': tie_breakers,
            })

        def _generate_confused_pinyin_variants(pinyin_text: str) -> list:
            variants = []
            if len(pinyin_text) < 3:
                return variants
            for index, letter in enumerate(pinyin_text):
                for alt in PINYIN_CONFUSION_MAP.get(letter, ()):
                    variants.append((index, pinyin_text[:index] + alt + pinyin_text[index + 1:]))
            return variants

        rows = []
        for _, row in self._stock_name_code.iterrows():
            code = _as_text(row['code'])
            name = _as_text(row['name'])
            py = _as_text(row['pinyin']).upper()
            if not code or not name:
                continue
            rows.append((row, code, name, py))

        def _finalize_candidates(candidates: list) -> list:
            candidates.sort(key=lambda item: (item['_score'], item['_tie']))
            final_results = []
            seen_codes = set()
            for item in candidates:
                if item['code'] in seen_codes:
                    continue
                seen_codes.add(item['code'])
                final_results.append({
                    'code': item['code'],
                    'name': item['name'],
                    'market': item['market'],
                    'pinyin': item['pinyin']
                })
                if len(final_results) >= limit:
                    break
            return final_results

        if is_code_pattern:
            if '?' not in keyword_str:
                for row, code, _, _ in rows:
                    if keyword_str == code:
                        return [{
                            'code': code,
                            'name': _as_text(row['name']),
                            'market': _as_text(row['market']),
                            'pinyin': _as_text(row['pinyin'])
                        }]
                return []

            candidates = []
            match_indexes = [idx for idx, ch in enumerate(keyword_str) if ch != '?']
            for row, code, _, _ in rows:
                if all(code[idx] == keyword_str[idx] for idx in match_indexes):
                    _append_candidate(candidates, row, 0, (code,))
            return _finalize_candidates(candidates)

        if has_chinese:
            for row, _, name, _ in rows:
                if keyword_str == name:
                    return [{
                        'code': _as_text(row['code']),
                        'name': name,
                        'market': _as_text(row['market']),
                        'pinyin': _as_text(row['pinyin'])
                    }]

            candidates = []
            for row, code, name, _ in rows:
                if name.startswith(keyword_str):
                    _append_candidate(candidates, row, 0, (-len(keyword_str), len(name), code))
            if candidates:
                return _finalize_candidates(candidates)

            if len(keyword_str) >= 2:
                candidates = []
                for row, code, name, _ in rows:
                    if keyword_str in name:
                        _append_candidate(candidates, row, 0, (name.find(keyword_str), len(name), code))
                if candidates:
                    return _finalize_candidates(candidates)

            if len(keyword_str) >= 3 and converted_pinyin:
                strong_typo_candidates = []
                weak_typo_candidates = []
                for row, code, name, _ in rows:
                    distance = _char_distance(keyword_str, name)
                    if distance == 1:
                        diff_index = next(i for i, (lch, rch) in enumerate(zip(keyword_str, name)) if lch != rch)
                        prefix_len = _common_prefix_len(keyword_str, name)
                        suffix_len = _common_suffix_len(keyword_str, name)
                        same_first = 1 if keyword_str[0] == name[0] else 0
                        typo_pinyin_distance = _edit_distance(
                            _generate_full_pinyin(keyword_str[diff_index]),
                            _generate_full_pinyin(name[diff_index])
                        )
                        target_candidates = strong_typo_candidates if same_first and typo_pinyin_distance <= 1 else weak_typo_candidates
                        _append_candidate(
                            target_candidates,
                            row,
                            0,
                            (-same_first, typo_pinyin_distance, -prefix_len, -suffix_len, len(name), code)
                        )
                if strong_typo_candidates:
                    return _finalize_candidates(strong_typo_candidates)

                candidates = []
                for row, code, _, py in rows:
                    if converted_pinyin == py:
                        _append_candidate(candidates, row, 0, (len(py), code))
                if candidates:
                    return _finalize_candidates(candidates)

                if weak_typo_candidates:
                    return _finalize_candidates(weak_typo_candidates)

                candidates = []
                for row, code, _, py in rows:
                    if py.startswith(converted_pinyin):
                        _append_candidate(candidates, row, 0, (-len(converted_pinyin), len(py), code))
                if candidates:
                    return _finalize_candidates(candidates)

                candidates = []
                for row, code, _, py in rows:
                    if converted_pinyin in py:
                        _append_candidate(candidates, row, 0, (py.find(converted_pinyin), len(py), code))
                if candidates:
                    return _finalize_candidates(candidates)

                confused_variants = _generate_confused_pinyin_variants(converted_pinyin)

                candidates = []
                for position, variant in confused_variants:
                    for row, code, _, py in rows:
                        if py == variant:
                            _append_candidate(candidates, row, 0, (position, len(py), code))
                if candidates:
                    return _finalize_candidates(candidates)

                candidates = []
                for position, variant in confused_variants:
                    for row, code, _, py in rows:
                        if py.startswith(variant):
                            _append_candidate(candidates, row, 0, (position, -len(variant), len(py), code))
                if candidates:
                    return _finalize_candidates(candidates)

            return []

        candidates = []
        for row, code, _, py in rows:
            if keyword_upper == py:
                _append_candidate(candidates, row, 0, (len(py), code))
        if candidates:
            return _finalize_candidates(candidates)

        candidates = []
        for row, code, _, py in rows:
            if py.startswith(keyword_upper):
                _append_candidate(candidates, row, 0, (-len(keyword_upper), len(py), code))
        if candidates:
            return _finalize_candidates(candidates)

        candidates = []
        for row, code, _, py in rows:
            if keyword_upper in py:
                _append_candidate(candidates, row, 0, (py.find(keyword_upper), len(py), code))
        if candidates:
            return _finalize_candidates(candidates)

        return []

    def export_to_csv(self, file_path: str):
        '''
        导出股票名称代码表到CSV文件
        '''
        if not self._stock_name_code.empty:
            self._stock_name_code.to_csv(file_path, index=False, encoding='utf-8')
    
    @staticmethod
    def get_stock_code_by_english_name(name: str):
        '''
        获取股票英文名称对应的股票代码
        '''
        response = StockNameCodeHelper.get_stock_info_by_english_name(name)
        if response:
            res = response.get('symbol', None)
        else:
            res = None
        return res

    @staticmethod
    def get_stock_info_by_english_name(name: str):
        '''
        获取股票英文名称对应的股票名称和股票代码等信息
        '''
        response = search_yahoo_finance(name)
        # print(response)
        if response:
            quotes = response.get('quotes', [])
            res = quotes[0] if quotes else None
            if res is None and "(" in name and ")" in name:
                res = StockNameCodeHelper.get_stock_info_by_english_name(name.split("(")[0].strip()) # pragma: no cover
        else:
            res = None
        return res
