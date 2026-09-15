import process
import os
from pathlib import Path
from process import logger


usuario = os.getlogin()

# Pasta raiz do projets


# Pega o usuário padrão da pessoa
dominio_interno = usuario

# Pasta MASTER
datalake = f'C:/Users/{dominio_interno}/Numerator International/BKO - Documents/projeto-dados-ops'

# Pasta Dominio Interno
pasta_ficha = '/do_ficha/tc/input_bruto'
pasta_domicilios = '/do_bases/TopClient'
pasta_all_pre = '/do_preal_fornecedor/ref_cosolidado'
pasta_gacode = '/do_gacode'
pasta_output = '/do_ficha/tc/output_validacao'
pasta_per_produtivo = '/do_calendario_fiscal'
pasta_engj ='/do_ficha/tc/output_engj'
pasta_rep7 = '/do_rep7'
pasta_engj ='/do_ficha/tc/output_engj'
pasta_mort = '/do_mortos'


def carregar_dados():
    logger.write( etapa='Charge', mensagem=f'ref usuario: {dominio_interno}')
    # Ficha de cadastro do panelista
    logger.write( etapa='Charge', mensagem='ref periodo produtivo')    
    df_periodo = process.carregamento(    
        path = Path(datalake + pasta_per_produtivo),
        prefixo = 'do_cal'
    )

    logger.write( etapa='Charge', mensagem='ref fichas fornecedor')    
    # Ficha de cadastro do panelista
    df_ficha = process.carregamento(    
        path = Path(datalake + pasta_ficha),
        prefixo = 'ficha'
    )
    # Fast Normalization 
    df_ficha.loc[df_ficha['arquivo_origem'].str.startswith('ficha-backlog'), 'Status'] = 'BACKLOG'
    df_ficha.loc[df_ficha['arquivo_origem'].str.startswith('ficha-eligible'), 'Status'] = 'ENVIADO_WP'
    df_ficha.loc[df_ficha['arquivo_origem'].str.startswith('ficha-total'), 'Status'] = 'ENVIADO_WP_TOTAL'

    col = ['AVATAR FINALIZADO (BRT)','Gacode','Estado','Entrevistador#1','Entrevistador#2',
        'PanelSmart#1','PanelSmart#1.1','UserPS','Classe','P12a#1','P10a#1', 'P10b#1','P10d_t','P10e#2_t','Status']
    df_ficha['UserPS'] = df_ficha['PanelSmart#1'].astype(int) - 550000000
    # Lógica: não desejo informar. Retirar se precisar substituir o uso
    # df_ficha = df_ficha.loc[~df_ficha.eq('nao_desejo_informar').any(axis=1)].copy()
    # df_trat é a base de dados utilizada para o processamento subsequente
    df_trat = df_ficha[col].copy()

    # Domicilios Vivos
    logger.write( etapa='Charge', mensagem='ref domicilios vivos')    
    df_vivos = process.carregamento(
        path = Path(datalake + pasta_domicilios),
        prefixo = 'NRPerfil',
        hd = 14

    )
    # dados para validação no GPM vivos da topclient
    df_vivos.rename(columns={'FIPanel1':'Data_Entrada'}, inplace=True)
    df_vivos.iddomicilio = df_vivos.iddomicilio.astype(str)
    df_vivos = df_vivos.loc[df_vivos['Origen Proveedor'] == 'TOP Client'].copy()

    # dados para validar se está no GPM ou não
    df_vivos_geral = df_vivos[['iddomicilio', 'Data_Entrada','Origen Proveedor']].copy()

    # Referência de todos os id's consoidados top client
    logger.write( etapa='Charge', mensagem='ref prealocados fornecedor')    
    df_pre_aloc = process.carregamento(
        path = Path(datalake + pasta_all_pre),
        prefixo = 'consolidado'
    )
    df_origem_id = df_pre_aloc[['UserPS','Origen_GPM']].drop_duplicates().copy()
    df_origem_id.Origen_GPM = df_origem_id.Origen_GPM.replace('22 - Centro Oeste','22 - Centro-Oeste')
    df_origem_id.rename(columns={'Origen_GPM':'Pre_Origen'}, inplace=True)
    df_origem_id.UserPS = df_origem_id.UserPS.astype(str)

    logger.write(etapa='Charge', mensagem='ref regionalizacao interna') 
    df_gacode = process.carregamento(
    path = Path(datalake + pasta_gacode),
    prefixo = 'bs'
    )

  
    _, nm_arq = process.pegar_arquivo_recente(f'C:/Users/{dominio_interno}/Numerator International/BKO - Documents/projeto-dados-ops/do_rep7', extensao=None,posicao=1)
    print(nm_arq)
    logger.write(etapa='Charge', mensagem=f'ref rep7: {nm_arq}') 
    df_criterio = process.carregamento(
            path=Path(datalake + pasta_rep7),
            prefixo = nm_arq
        )
    df_criterio = df_criterio[['UserPS','DiaDeCompra','NumCompras']]
    
    _, nm_arq = process.pegar_arquivo_recente(f'C:/Users/{dominio_interno}/Numerator International/BKO - Documents/projeto-dados-ops{pasta_output}', extensao=None,posicao=1)
    logger.write( etapa='processamento', mensagem=f'ref carregamento dados validação: {nm_arq}')

    df_ls_batch = process.carregamento(
        path= Path(datalake + pasta_output),
        prefixo=nm_arq,
        sh = 'Detalhe Validação'
    )

    pst_egj = Path(datalake + pasta_engj)
    pst_out = Path(datalake + pasta_output)

    df_mortalidade = process.carregamento(
        path= Path(datalake + pasta_mort),
        prefixo= 'Mortalidades'
    )

    return df_periodo,df_trat,df_ficha,df_vivos,df_vivos_geral,df_origem_id,df_gacode,df_criterio,df_ls_batch,pst_egj,pst_out,df_mortalidade


