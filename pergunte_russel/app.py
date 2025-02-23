import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz
from unidecode import unidecode
import re

# Definir a senha do administrador
ADMIN_PASSWORD = "admin123"

# Carregar a planilha
@st.cache_data
def load_data():
    try:
        df = pd.read_excel(r"C:\\Users\\User\\Desktop\\INTELIGENCIA\\INT\\pergunte_russel\\base.xlsx")
        df["Palavras-Chave"] = df["Palavras-Chave"].astype(str)
        df["Palavras-Chave"] = df["Palavras-Chave"].apply(lambda x: [normalizar_texto(p) for p in x.split(",")])
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return pd.DataFrame()

# Salvar a planilha e limpar o cache corretamente
def save_data(df):
    try:
        df.to_excel("base.xlsx", index=False)
        st.success("Dados salvos com sucesso!")

        # Aguarda um tempo para evitar erro no Streamlit Cloud
        st.experimental_sleep(0.5)

        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar o arquivo: {e}")

# Função para normalizar texto
def normalizar_texto(texto):
    if isinstance(texto, str):
        texto = unidecode(texto.lower())
        texto = re.sub(r'[^\w\s]', '', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto
    return ""

# Função para encontrar resposta por palavras-chave
def encontrar_resposta_por_palavras_chave(prompt, df):
    prompt = normalizar_texto(prompt)
    melhor_pontuacao = 0
    melhor_resposta = None

    for _, row in df.iterrows():
        palavras_chave = row["Palavras-Chave"]

        if not isinstance(palavras_chave, list):
            continue

        pontuacoes = [fuzz.token_set_ratio(palavra, prompt) for palavra in palavras_chave]
        pontuacao = max(pontuacoes) if pontuacoes else 0

        if pontuacao > melhor_pontuacao and pontuacao >= 50:
            melhor_pontuacao = pontuacao
            melhor_resposta = row["Resposta"]

    return melhor_resposta if melhor_resposta else "Desculpe, não entendi. Pode reformular a pergunta?"

# Função principal para encontrar resposta
def encontrar_resposta(prompt, df):
    return encontrar_resposta_por_palavras_chave(prompt, df)

# Interface do app
st.title("Pergunte para o Russel 🤖")

# Seleção de modo (Colaborador ou Administrador)
modo = st.sidebar.radio("Selecione o modo:", ("Colaborador", "Administrador"))

df = load_data()

# Verifica se o DataFrame foi carregado corretamente
if df.empty:
    st.error("O arquivo está vazio ou não pôde ser carregado. Verifique o arquivo.")
    st.stop()

# Verifica se as colunas necessárias existem
colunas_necessarias = ["Pergunta", "Resposta", "Palavras-Chave"]
for coluna in colunas_necessarias:
    if coluna not in df.columns:
        st.error(f"O arquivo não contém a coluna '{coluna}'. Verifique o arquivo.")
        st.stop()

# Modo Colaborador
if modo == "Colaborador":
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Digite sua mensagem...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = encontrar_resposta(prompt, df)
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

# Modo Administrador com Senha
elif modo == "Administrador":
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.subheader("🔒 Acesso Restrito")
        senha = st.text_input("Digite a senha:", type="password")

        if st.button("Entrar"):
            if senha == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("Acesso permitido! ✅")
                st.experimental_sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Senha incorreta!")

    if st.session_state.admin_authenticated:
        st.header("Modo Administrador")
        st.write("Aqui você pode adicionar ou editar perguntas e respostas.")

        # Adicionar uma nova pergunta
        st.subheader("Adicionar Nova Pergunta")
        nova_pergunta = st.text_input("Digite a nova pergunta:")
        nova_resposta = st.text_input("Digite a resposta correspondente:")
        novas_palavras_chave = st.text_input("Digite as palavras-chave (separadas por vírgula):")

        if st.button("Adicionar Pergunta e Resposta"):
            if nova_pergunta and nova_resposta and novas_palavras_chave:
                novo_registro = pd.DataFrame({
                    "Pergunta": [nova_pergunta],
                    "Resposta": [nova_resposta],
                    "Palavras-Chave": [[normalizar_texto(p) for p in novas_palavras_chave.split(",")]]
                })
                df = pd.concat([df, novo_registro], ignore_index=True)
                save_data(df)
                st.success("Pergunta e resposta adicionadas com sucesso!")

                # Aguarda antes de recarregar
                st.experimental_sleep(0.5)
                st.rerun()
            else:
                st.error("Por favor, preencha todos os campos.")

        # Editar uma pergunta existente
        st.subheader("Editar Pergunta Existente")
        perguntas_existentes = df["Pergunta"].tolist()
        pergunta_selecionada = st.selectbox("Selecione uma pergunta para editar:", [""] + perguntas_existentes)

        if pergunta_selecionada:
            indice = df[df["Pergunta"] == pergunta_selecionada].index[0]

            pergunta_editada = st.text_input("Editar Pergunta:", df.at[indice, "Pergunta"])
            resposta_editada = st.text_input("Editar Resposta:", df.at[indice, "Resposta"])
            palavras_chave_editadas = st.text_input("Editar Palavras-Chave (separadas por vírgula):", 
                                                    ", ".join(df.at[indice, "Palavras-Chave"]))

            if st.button("Salvar Alterações"):
                df.at[indice, "Pergunta"] = pergunta_editada
                df.at[indice, "Resposta"] = resposta_editada
                df.at[indice, "Palavras-Chave"] = [normalizar_texto(p) for p in palavras_chave_editadas.split(",")]
                save_data(df)
                st.success("Alterações salvas com sucesso!")

                # Aguarda antes de recarregar para evitar erro
                st.experimental_sleep(0.5)
                st.rerun()

        # Exibir todas as perguntas cadastradas
        st.subheader("Perguntas Cadastradas")
        st.dataframe(df[["Pergunta", "Resposta", "Palavras-Chave"]])








