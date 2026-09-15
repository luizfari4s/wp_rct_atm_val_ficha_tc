import pandas as pd
import os
from datetime import datetime
from pathlib import Path

import warnings

warnings.filterwarnings("ignore", message="DataFrame is highly fragmented", category=pd.errors.PerformanceWarning)

usuario = os.getlogin()
def obter_periodo_produtivo(data, periodo):
    linha = periodo.loc[
        (periodo["Desde"] <= data) &
        (periodo["Hasta"] >= data)
    ]

    if not linha.empty:
        ano = linha.iloc[0]["Ano"]
        mes = linha.iloc[0]["Mes"]
        return f"{ano}-{mes:02d}"  # Ex.: 2026-07

    return pd.NA

def tel_number_pdr_val(df, col1):

    df = df.copy()

    nm = 'Telefone_NRZD'

    df[nm] = (
        df[col1]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", "", regex=True)
        .str.replace(r"[^\d]", "", regex=True)
    )

    # Remove código do país apenas quando fizer sentido
    df[nm] = df[nm].apply(
        lambda x: x[2:] if x.startswith("55") and len(x) >= 12 else x
    )

    # Remove zeros à esquerda DEPOIS
    df[nm] = df[nm].str.replace(r"^0+", "", regex=True)

    return df

def email_pdr_val(df, col1):
    df = df.copy()

    nm = 'Email_NRZD'

    # Normalização
    df[nm] = (
        df[col1]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r'\s+', '', regex=True)
    )

    # Validação da estrutura
    email_regex = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'

    df['em_validacao'] = (
        df[nm]
        .str.match(email_regex, na=False)
    )

    return df

def carregamento(prefixo, path, hd=None,fluxo_externo=False,sh=None):
    import pandas as pd
    import glob
    import os

    arquivos = (
        glob.glob(os.path.join(path, f"{prefixo}*.csv"))
        + glob.glob(os.path.join(path, f"{prefixo}*.xlsx"))
        + glob.glob(os.path.join(path, f"{prefixo}*.xls"))
    )

    dfs = []

    for arq in arquivos:

        extensao = os.path.splitext(arq)[1].lower()

        if extensao == ".csv":
            df = pd.read_csv(arq, sep=';', low_memory=False)

        elif extensao in [".xlsx", ".xls"]:

            if sh is not None:
                df = pd.read_excel(arq, sheet_name=sh)

            elif hd is not None:
                df = pd.read_excel(arq, header=hd)

            else:
                df = pd.read_excel(arq)
        else:
            continue

        # Sempre guarda a origem
        df['arquivo_origem'] = os.path.basename(arq)

        dfs.append(df)

    if not dfs:
        raise ValueError("Nenhum arquivo encontrado para o prefixo informado.")

    df_final = pd.concat(dfs, ignore_index=True)

    # Remove apenas no fluxo externo
    if fluxo_externo:
        df_final.drop(columns='arquivo_origem', inplace=True)

    return df_final

def pegar_arquivo_recente(pasta, extensao=None, posicao=1):
    """
    Retorna o n-ésimo arquivo mais recente de uma pasta.

    Parâmetros:
        pasta (str): Caminho da pasta.
        extensao (str ou tuple, opcional): Ex.: '.csv', '.xlsx'.
        posicao (int): 1 = mais recente, 2 = penúltimo, 3 = antepenúltimo...

    Retorna:
        str | None: Caminho completo do arquivo ou None se não existir.
    """

    arquivos = [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if os.path.isfile(os.path.join(pasta, f))
    ]

    if extensao:
        arquivos = [
            f for f in arquivos
            if f.lower().endswith(extensao if isinstance(extensao, tuple) else extensao.lower())
        ]

    if len(arquivos) < posicao:
        return None

    arquivos_ordenados = sorted(
        arquivos,
        key=os.path.getctime,
        reverse=True
    )
    arquivo = arquivos_ordenados[posicao - 1]
    return arquivo, os.path.splitext(os.path.basename(arquivo))[0]

class Logger:

    data_hora = datetime.now()

    def __init__(self):

        os.makedirs('logs', exist_ok=True)

        # Puxa o arquivo config dentro da pasta do projeto 
        PASTA_PROJETO = Path(__file__).resolve().parent
        ARQUIVO_CONFIG = PASTA_PROJETO / "config.xlsx"
        config = pd.read_excel(ARQUIVO_CONFIG)

        # Analisa e coloca no ambiente a pasta onde ira salvar os logs do processoamento
        # Feito isso, ele já salva os dadoa da execução automatizamente
        caminho = config.loc[
        config["chave"] == "logs_atm_val_ficha_tc","caminho"].iloc[0]

        'C:/Users/luiz.farias/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/logs/pipeline_%Y%m%d.csv'
        self.log_file = datetime.now().strftime(
            caminho + 'logs_atm_val_ficha_tc_%Y%m%d.csv'
        )


    def write(
        self,
        etapa,
        status='INFO',
        mensagem='',
        detalhes=''
    ):

        log = pd.DataFrame([{
            'datetime': datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S'
            ),
            'etapa': etapa,
            'status': status,
            'mensagem': mensagem,
            'detalhes': detalhes
        }])
        # Mostra em tempo de execução
        print(
            f'[{self.data_hora}] [{status}] [{etapa}] {mensagem}'
        )

        if not os.path.exists(self.log_file):

            log.to_csv(
                self.log_file,
                index=False,
                sep=';'
            )

        else:

            log.to_csv(
                self.log_file,
                mode='a',
                header=False,
                index=False,
                sep=';'
            )
logger = Logger()




