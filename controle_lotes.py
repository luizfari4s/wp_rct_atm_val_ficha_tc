from pandas import to_datetime
from process import logger
from process import obter_periodo_produtivo
from datetime import datetime

def controle_lotes(df_ids_recrutados_origen_validacao,df_ls_batch,df_periodo,df_vivos_geral):
    logger.write( etapa='processamento', mensagem=f'ref processamento do ultimo lote de dados')

    # Carregamento dos dados do ultimo arquivo processado 
    df_ls_batch = df_ls_batch[['PanelSmart#1','Lote','Data_inicio_importacao','data_processamento']]

    df_ls_batch['PanelSmart#1'] = df_ls_batch['PanelSmart#1'].astype(str)

    df_ls_batch.dropna(subset='PanelSmart#1',inplace=True)

    logger.write( etapa='processamento', mensagem=f'ref identificacao data-entrada_gpm')
    # Data da base
    df_ids_recrutados_origen_validacao["Data_Entrada_GPM"] = to_datetime(
        df_ids_recrutados_origen_validacao["Data_Entrada"],
        format="%d/%m/%Y"
    )

    # Datas do calendário produtivo
    df_periodo["Desde"] = to_datetime(df_periodo["Desde"])
    df_periodo["Hasta"] = to_datetime(df_periodo["Hasta"])

    # Fast normalization
    df_ls_batch['PanelSmart#1'] = df_ls_batch['PanelSmart#1'].astype(float).astype(int).astype(str)


    df_ids_recrutados_origen_validacao['mes_produtivo'] = df_ids_recrutados_origen_validacao["Data_Entrada_GPM"].apply(
        lambda x: obter_periodo_produtivo(x, df_periodo)
    )

    logger.write( etapa='processamento', mensagem=f'ref geracao lote pendente do recrutamento para importação')

    df_rct_batch_vivos_pend_importacao = df_ids_recrutados_origen_validacao.merge(df_ls_batch, on='PanelSmart#1', how='left').copy()


    df_rct_batch_vivos_pend_importacao["dt_ficha"] = (to_datetime(
    df_rct_batch_vivos_pend_importacao["AVATAR FINALIZADO (BRT)"],
    format="%d/%m/%Y %H:%M",
    dayfirst=True
    ).dt.normalize()
    )
    df_rct_batch_vivos_pend_importacao['mes_produtivo_ficha'] = df_rct_batch_vivos_pend_importacao["dt_ficha"].apply(
        lambda x: obter_periodo_produtivo(x, df_periodo)
    )


    df_rct_batch_vivos_pend_importacao['mes_produtivo_ficha'] = df_rct_batch_vivos_pend_importacao["dt_ficha"].apply(
        lambda x: obter_periodo_produtivo(x, df_periodo)
    ) 


    df_rct_batch_vivos_pend_importacao['mes_produtivo_ficha'] = df_rct_batch_vivos_pend_importacao["dt_ficha"].apply(
        lambda x: obter_periodo_produtivo(x, df_periodo)
    ) 

    
    logger.write( etapa='processamento', mensagem=f'ref separacao BACKLOG & ENVIADO_WP')


    hoje = datetime.now()

    periodo_real = obter_periodo_produtivo(hoje, df_periodo)

    df_rct_batch_vivos_pend_importacao.loc[
        (df_rct_batch_vivos_pend_importacao.mes_produtivo == periodo_real) &
        (df_rct_batch_vivos_pend_importacao.Status.isna()), 'Status'] = 'FICHA_VALIDADA_PERIODO_ANTERIOR'

    df_rct_batch_vivos_pend_importacao = df_rct_batch_vivos_pend_importacao[
        (df_rct_batch_vivos_pend_importacao["Status"]).isin(['BACKLOG','ENVIADO_WP','ENVIADO_WP_TOTAL']) |
        (to_datetime(df_rct_batch_vivos_pend_importacao["mes_produtivo"]).dt.month == hoje.month) &
        (to_datetime(df_rct_batch_vivos_pend_importacao["mes_produtivo"]).dt.year == hoje.year)
    ]

    logger.write( etapa='processamento', mensagem=f'ref aplicação periodo produtivo')

    data_processamento = datetime.now()
    
    logger.write( etapa='processamento', mensagem=f'ref classificação de lotes & data de processamento')

    lote = f"GPM_{data_processamento.strftime('%Y%m%d_%H%M%S')}"
    
    mask = (
        df_rct_batch_vivos_pend_importacao["Decisao_Final"].isin([
            "SUBIR GPM",
            "SUBIR GPM - AJUSTAR ORIGEM",
            "SUBIR GPM - CRITERIO DE QUALIDADE (<25 ATOS)"
        ])
        & df_rct_batch_vivos_pend_importacao["Lote"].isna() & df_rct_batch_vivos_pend_importacao["data_processamento"].isna()
    )
    
    
    
    df_rct_batch_vivos_pend_importacao.loc[mask, "Lote"] = lote
    df_rct_batch_vivos_pend_importacao.loc[mask, "Data_inicio_importacao"] = data_processamento
    df_rct_batch_vivos_pend_importacao.loc[mask, "data_processamento"] = str(data_processamento)

    df_rct_batch_vivos_pend_importacao['gpm'] = df_rct_batch_vivos_pend_importacao['PanelSmart#1'].isin(df_vivos_geral['iddomicilio'])

    df_rct_batch_vivos_pend_importacao.loc[df_rct_batch_vivos_pend_importacao.mes_produtivo.isna(), 'mes_produtivo'  ] = None

    df_rct_batch_vivos_pend_importacao.loc[
        df_rct_batch_vivos_pend_importacao['Lote'].isna(),
        'Lote'
    ] = (
        'Lote Processo Manual -'
        + df_rct_batch_vivos_pend_importacao.loc[df_rct_batch_vivos_pend_importacao['Lote'].isna(), 'Data_Entrada_GPM'].astype(str)
    )


    return df_rct_batch_vivos_pend_importacao



















