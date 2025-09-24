
import streamlit as st
import pandas as pd
import plotly.express as px
from utils import process_data, generate_alerts, detect_columns
from io import BytesIO

st.set_page_config(page_title="FarolPedagogico — Painel SGE", layout="wide", page_icon="🚦")

# Simple login (test credentials admin/admin)
def login_widget():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        col1, col2 = st.columns([9,1])
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
        return True
    else:
        st.sidebar.markdown("### 🔐 Login")
        username = st.sidebar.text_input("Usuário")
        password = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            if username == "admin" and password == "admin":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.sidebar.error("Credenciais inválidas — use `admin`/`admin` como teste.")
        st.sidebar.markdown("---")
        return False

logged = login_widget()
st.title("FarolPedagogico — Painel SGE")
st.caption("Painel com aba dedicada para Gestão de Evasão — protótipo")

# Upload / example
uploaded = st.file_uploader("📂 Envie o arquivo .xlsx do SGE", type=["xlsx"])
if st.button("🔁 Usar dados de exemplo (teste)"):
    df = pd.DataFrame({
        "Nome do Aluno": ["Ana","Bruno","Carlos","Diana","Eduardo","Fábio","Gabriela"],
        "Turma": ["A","A","B","B","A","C","C"],
        "Disciplina": ["Matematica","Portugues","Matematica","Portugues","Matematica","Portugues","Matematica"],
        "Nota 1": [5.0, 8.0, 4.5, 7.0, 3.0, 9.0, 2.5],
        "Nota 2": [6.0, 7.5, 5.0, 6.0, 4.0, 8.5, 3.0],
        "Frequencia": [90,95,40,88,20,60,50],
        "Escola": ["Escola X","Escola X","Escola X","Escola Y","Escola X","Escola Y","Escola Y"]
    })
    df_processed = process_data(df)
elif uploaded is not None:
    try:
        df_raw = pd.read_excel(uploaded)
        df_processed = process_data(df_raw)
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        st.stop()
else:
    st.info("Ainda sem arquivo carregado. Faça upload de um .xlsx do SGE ou use o botão de exemplo.")
    st.stop()

# show detected columns
detected = detect_columns(df_processed)
with st.expander("Colunas detectadas (mapa)"):
    st.write(detected)

# Page selector
page = st.sidebar.radio("Ir para", ["Painel", "Gestão de Evasão", "Exportar / Relatórios"])

# Common filters in sidebar
st.sidebar.header("Filtros comuns")
escola_opt = None
if "escola" in df_processed.columns:
    escola_opt = st.sidebar.selectbox("Escola", options=["Todas"] + sorted(df_processed["escola"].dropna().unique().tolist()))
turma_opt = st.sidebar.selectbox("Turma", options=["Todas"] + sorted(df_processed["turma"].dropna().unique().tolist()) if "turma" in df_processed.columns else ["Todas"])
disciplina_opt = st.sidebar.multiselect("Disciplina (multi)", options=sorted(df_processed["disciplina"].dropna().unique().tolist()) if "disciplina" in df_processed.columns else [], default=[])
aluno_opt = st.sidebar.selectbox("Aluno", options=["Todos"] + sorted(df_processed["aluno"].dropna().unique().tolist()) if "aluno" in df_processed.columns else ["Todos"])

# Evasion controls
st.sidebar.markdown("---")
st.sidebar.header("Evasão")
include_evadidos = st.sidebar.checkbox("Incluir evadidos na análise (freq < 75%)?", value=True)
only_evadidos = st.sidebar.checkbox("Mostrar apenas evadidos?", value=False)
evade_threshold = st.sidebar.slider("Limiar de evasão (%)", min_value=0, max_value=100, value=75)

# Apply filters helper
def apply_filters(df):
    df_f = df.copy()
    if escola_opt and escola_opt != "Todas":
        df_f = df_f[df_f["escola"] == escola_opt]
    if turma_opt and turma_opt != "Todas":
        df_f = df_f[df_f["turma"] == turma_opt]
    if disciplina_opt and len(disciplina_opt) > 0:
        df_f = df_f[df_f["disciplina"].isin(disciplina_opt)]
    if aluno_opt and aluno_opt != "Todos":
        df_f = df_f[df_f["aluno"] == aluno_opt]
    if "frequencia" in df_f.columns:
        if not include_evadidos:
            df_f = df_f[df_f["frequencia"] >= evade_threshold]
        if only_evadidos:
            df_f = df_f[df_f["frequencia"] < evade_threshold]
    return df_f

df_filtered = apply_filters(df_processed)

if page == "Painel":
    # Top cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Registros", f"{len(df_filtered):,}")
    with col2:
        st.metric("Alunos (únicos)", df_filtered['aluno'].nunique() if 'aluno' in df_filtered.columns else 0)
    with col3:
        st.metric("Turmas", df_filtered['turma'].nunique() if 'turma' in df_filtered.columns else 0)
    with col4:
        abaixo = int(df_filtered[df_filtered.get('media12', 0) < 6].shape[0]) if 'media12' in df_filtered.columns else 0
        st.metric("Notas < 6 (registros)", abaixo)

    st.markdown("---")
    if "classificacao" in df_filtered.columns:
        fig = px.pie(df_filtered, names="classificacao", title="Distribuição de classificação")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("## 🔥 Relatório — Alunos em risco")
    alerts = generate_alerts(df_filtered)
    st.write(f"Total de alertas (média < 6): **{len(alerts)}**")
    if not alerts.empty:
        display_cols = [c for c in ["aluno","turma","disciplina","n1","n2","media12","frequencia","classificacao"] if c in alerts.columns]
        styled = alerts[display_cols].copy()
        if "media12" in styled.columns:
            styled = styled.sort_values("media12")
        styled_display = styled.style.applymap(lambda v: "background-color: #ffcccc" if (isinstance(v,(int,float)) and v<6) else "", subset=["media12"])
        st.dataframe(styled_display, height=350)
        buf = BytesIO()
        styled.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        st.download_button("📥 Baixar relatório filtrado (Excel)", data=buf, file_name="relatorio_filtrado.xlsx", mime="application/vnd.openxmlformats-officedocument-spreadsheetml.sheet")
    else:
        st.success("Nenhum aluno com média abaixo de 6 nos dados filtrados.")

elif page == "Gestão de Evasão":
    st.header("Gestão de Evasão — Análise por Turma e Disciplina")
    if "frequencia" not in df_processed.columns:
        st.warning("Coluna de frequência não encontrada na planilha — não é possível rodar a análise de evasão.")
    else:
        # compute evasion flag
        df_processed['evadido'] = df_processed['frequencia'] < evade_threshold
        df_evad = df_processed[df_processed['evadido'] == True]
        st.write(f"Total de evadidos no conjunto (frequência < {evade_threshold}%): **{len(df_evad)}**")

        # Ranking turmas
        rank_turma = df_evad.groupby('turma').size().reset_index(name='evadidos').sort_values('evadidos', ascending=False)
        if not rank_turma.empty:
            fig1 = px.bar(rank_turma, x='turma', y='evadidos', title='Turmas com mais evadidos', text='evadidos')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Nenhum evadido por turma.")

        # Ranking disciplinas
        rank_disc = df_evad.groupby('disciplina').size().reset_index(name='evadidos').sort_values('evadidos', ascending=False)
        if not rank_disc.empty:
            fig2 = px.bar(rank_disc, x='disciplina', y='evadidos', title='Disciplinas com mais evadidos', text='evadidos')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhum evadido por disciplina.")

        st.markdown("### Lista detalhada de evadidos")
        cols_show = [c for c in ['aluno','turma','disciplina','frequencia','media12','classificacao'] if c in df_evad.columns]
        if not df_evad.empty:
            df_list = df_evad[cols_show].sort_values('frequencia')
            st.dataframe(df_list, height=350)
            buf = BytesIO()
            df_list.to_excel(buf, index=False, engine='openpyxl')
            buf.seek(0)
            st.download_button("📥 Baixar lista de evadidos (Excel)", data=buf, file_name="evadidos.xlsx", mime="application/vnd.openxmlformats-officedocument-spreadsheetml.sheet")
        else:
            st.info("Nenhum aluno marcado como evadido.")

elif page == "Exportar / Relatórios":
    st.header("Exportar e Relatórios")
    st.markdown("Use os botões abaixo para exportar conjuntos de dados filtrados ou relatórios gerenciais.")
    # Export full filtered dataset
    buf_all = BytesIO()
    df_filtered.to_excel(buf_all, index=False, engine='openpyxl')
    buf_all.seek(0)
    st.download_button("📥 Baixar conjunto filtrado (Excel)", data=buf_all, file_name="dados_filtrados.xlsx", mime="application/vnd.openxmlformats-officedocument-spreadsheetml.sheet")
    # Export alerts only
    alerts = generate_alerts(df_filtered)
    buf_alerts = BytesIO()
    alerts.to_excel(buf_alerts, index=False, engine='openpyxl')
    buf_alerts.seek(0)
    st.download_button("📥 Baixar apenas alertas (Excel)", data=buf_alerts, file_name="alertas.xlsx", mime="application/vnd.openxmlformats-officedocument-spreadsheetml.sheet")
