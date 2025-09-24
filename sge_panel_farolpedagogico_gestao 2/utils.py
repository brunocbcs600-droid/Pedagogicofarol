
import pandas as pd

COMMON_MAP = {
    'aluno': ['aluno','nome do aluno','nome','student','student_name'],
    'turma': ['turma','classe','class','group'],
    'disciplina': ['disciplina','materia','subject','disciplines'],
    'n1': ['nota 1','nota1','n1','primeira nota','nota_1'],
    'n2': ['nota 2','nota2','n2','segunda nota','nota_2'],
    'media12': ['media12','media 12','media','média','media_1_2'],
    'escola': ['escola','school','unidade'],
    'frequencia': ['frequencia','frequência','freq','presenca','% presença','presença']
}

def find_column(df_cols, candidates):
    df_cols_l = [str(c).strip().lower() for c in df_cols]
    for cand in candidates:
        if cand.lower() in df_cols_l:
            return [orig for orig in df_cols if str(orig).strip().lower()==cand.lower()][0]
    # partial match
    for cand in candidates:
        for orig in df_cols:
            if cand.lower() in str(orig).strip().lower():
                return orig
    return None

def process_data(df):
    out = df.copy()
    cols = list(out.columns)
    rename_map = {}
    for key, variants in COMMON_MAP.items():
        found = find_column(cols, variants)
        if found:
            rename_map[found] = key
    if rename_map:
        out = out.rename(columns=rename_map)
    out.columns = [str(c).strip().lower() for c in out.columns]
    # numeric conversion
    if 'n1' in out.columns:
        out['n1'] = pd.to_numeric(out['n1'], errors='coerce')
    if 'n2' in out.columns:
        out['n2'] = pd.to_numeric(out['n2'], errors='coerce')
    if 'n1' in out.columns and 'n2' in out.columns:
        out['media12'] = (out['n1'].fillna(0) + out['n2'].fillna(0)) / 2
    if 'frequencia' in out.columns:
        out['frequencia'] = pd.to_numeric(out['frequencia'], errors='coerce')
    if 'media12' in out.columns:
        out['classificacao'] = out['media12'].apply(lambda x: 'Abaixo da Média' if x < 6 else 'Dentro da Meta')
    return out

def generate_alerts(df):
    if 'media12' in df.columns:
        cols = [c for c in ['aluno','turma','disciplina','n1','n2','media12','frequencia','classificacao'] if c in df.columns]
        return df[df['media12'] < 6][cols].copy()
    else:
        return pd.DataFrame()

def detect_columns(df):
    cols = list(df.columns)
    mapping = {}
    for key, variants in COMMON_MAP.items():
        found = find_column(cols, variants)
        mapping[key] = found
    return mapping
