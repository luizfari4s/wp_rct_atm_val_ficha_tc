import pandas as pd
import unicodedata
from process import logger
import numpy as np

def origen_analisys(vl_atos_recrutamento,df_gacode,df_origem_id):

    logger.write( etapa='processamento', mensagem=f'ref criação de chaves de enriquecimento de dados')
   
    # Enriquecimento Regioes
    df_regioes_estado = df_gacode[['NM_UF', 'NM_REGIAO']].drop_duplicates()
    df_regioes_estado.rename(columns={'NM_UF':'Estado'}, inplace=True)

    # Cruzamento para obser a região do estado
    vl_atos_recrutamento = vl_atos_recrutamento.merge(df_regioes_estado, on='Estado', how='left')

    # Criação da chave de setor para validação do GA Code
    vl_atos_recrutamento['chave_setor'] = vl_atos_recrutamento['NM_REGIAO'] + '-' + vl_atos_recrutamento['Estado'] + '-' + vl_atos_recrutamento['Entrevistador#1']

    
    # Normlaização de dados 
    vl_atos_recrutamento["chave_setor"] = vl_atos_recrutamento["chave_setor"].apply(
        lambda x: unicodedata.normalize("NFKD", x)
        .encode("ASCII", "ignore")
        .decode("ASCII")
        if pd.notna(x) else x   
    )

    # Normalização e criação de chaves de setor
    df_gacode['chave_setor'] = df_gacode['NM_REGIAO'] + '-' + df_gacode['NM_UF'] + '-' + df_gacode['NM_MUN']

    logger.write( etapa='processamento', mensagem=f'ref preparação base regionalização por setor')
    # Criação da base de validação de regionalização por setor
    df_origem = df_gacode[['NM_REGIAO','chave_setor','Região Kantar PNC 32 REGIONES','Região Expansão 2024','Origem_GPM_32','Origem_GPM_42','GACODE_KANTAR_Nuevo']].drop_duplicates(subset='chave_setor',).copy()
    df_origem.rename(columns={
        'Origem_GPM_32':"Origen_Recrutado_32_IHS",
        'Origem_GPM_42':"Origen_Recrutado_42_Expansao",

    },inplace=True)
    df_origem["chave_setor"] = df_origem["chave_setor"].apply(
        lambda x: unicodedata.normalize("NFKD", x)
        .encode("ASCII", "ignore")
        .decode("ASCII")
        if pd.notna(x) else x
    )

    logger.write( etapa='processamento', mensagem=f'ref enriquecimento de bases vl_atos_recrutamento')
    # Cruzamento final
    df_ids_recrutados_origen_validacao = vl_atos_recrutamento.merge(df_origem, on='chave_setor', how='left')
    df_ids_recrutados_origen_validacao = df_ids_recrutados_origen_validacao.merge(df_origem_id, left_on='PanelSmart#1',right_on='UserPS', how='left')

    return df_ids_recrutados_origen_validacao

def analise_segmentacao_origens(df_ids_recrutados_origen_validacao):
    

    # Colunas que representam as origens encontradas pela chave de setor
    cols_origem = ['Origen_Recrutado_32_IHS', 'Origen_Recrutado_42_Expansao']
    
    logger.write( etapa='processamento', mensagem=f'ref limpeza de pre-segmentacao')
    # Limpeza (caso o Excel tenha trazido #N/A como texto)
    df_ids_recrutados_origen_validacao[cols_origem] = df_ids_recrutados_origen_validacao[cols_origem].replace(['#N/A', '', 'nan', 'None'], np.nan)

    logger.write( etapa='processamento', mensagem=f'ref separacao regioes nao pertencentes ao desenho amostral')
    # 1. O setor não pertence a nenhum desenho amostral?
    cond_setor_nao_contemplado = df_ids_recrutados_origen_validacao[cols_origem].isna().all(axis=1)

    # 2. A pré-origem está entre as origens válidas daquele setor?
    cond_origem_correta = df_ids_recrutados_origen_validacao[cols_origem].eq(df_ids_recrutados_origen_validacao['Pre_Origen'], axis=0).any(axis=1)

    

    logger.write( etapa='processamento', mensagem=f'ref separacao regioes nao pertencentes ao desenho amostral')
    # Resultado final
    df_ids_recrutados_origen_validacao['Validacao_Origem'] = np.select(
        [
            cond_setor_nao_contemplado,
            cond_origem_correta
        ],
        [
            'SETOR_NAO_CONTEMPLADO',
            'ORIGEM_CORRETA'
        ],
        default='ORIGEM_INCORRETA'
    )

    # Separação duplicidades
    # Coluna de email 'P10d_t'
        
    logger.write( etapa='processamento', mensagem=f'ref seg aprovacao por origem')

    cond_aprovado = (
        (df_ids_recrutados_origen_validacao['Validacao_Origem'] == 'ORIGEM_CORRETA') &
        (df_ids_recrutados_origen_validacao['saida_decisao'] != 'AGUARDAR') &
        (df_ids_recrutados_origen_validacao['Data_Entrada'].isna())
    )

    logger.write( etapa='processamento', mensagem=f'ref ajuste posterior origem')

    cond_ajustar_origem = (
        (df_ids_recrutados_origen_validacao['Validacao_Origem'] == 'ORIGEM_INCORRETA') &
        (df_ids_recrutados_origen_validacao['saida_decisao'] != 'AGUARDAR') &
        (df_ids_recrutados_origen_validacao['Data_Entrada'].isna())
    )

    cond_setor= (
        df_ids_recrutados_origen_validacao['Validacao_Origem'] == 'SETOR_NAO_CONTEMPLADO'
    )

    logger.write( etapa='processamento', mensagem=f'ref ajuste posterior origem')
    cond_qualidade = (
        (df_ids_recrutados_origen_validacao['saida_decisao'] == 'AGUARDAR') &
        (df_ids_recrutados_origen_validacao['Validacao_Origem'].isin(['ORIGEM_CORRETA','ORIGEM_INCORRETA'])) & 
        (df_ids_recrutados_origen_validacao['NumCompras'] >= 5) &
        (df_ids_recrutados_origen_validacao['Data_Entrada'].isna())
        
    )


    cond_gom = (
        ~df_ids_recrutados_origen_validacao['Data_Entrada'].isna()
    )

    logger.write( etapa='processamento', mensagem=f'ref regra hard code linha 122 origen_analisys (revisar)')
    cond_teste =(
        df_ids_recrutados_origen_validacao['P10d_t'].isin(['teste@gmail.com',
                                                        'admin@gmail.com',
                                                        'ifoodteste7422@gmail.com'])
    )

    cond_mortalidade =(
        df_ids_recrutados_origen_validacao['FSPanel1'].notna()
    )

    cond_abaixo_5_atos = (
    (df_ids_recrutados_origen_validacao['saida_decisao'] == 'AGUARDAR') &
    (df_ids_recrutados_origen_validacao['NumCompras'] < 5) &
    (df_ids_recrutados_origen_validacao['Data_Entrada'].isna())
    )
    logger.write( etapa='processamento', mensagem=f'ref segmentação de bases para importação mediante regras')
    df_ids_recrutados_origen_validacao['Decisao_Final'] = np.select(
        [
            cond_teste,
            cond_mortalidade,
            cond_aprovado,
            cond_abaixo_5_atos,
            cond_ajustar_origem,
            cond_setor,
            cond_qualidade,
            cond_gom
            
        ],
        [
            'OFF - TESTE',
            'OFF - MORTALIDADE',
            'SUBIR GPM',
            'OFF - ABAIXO DE 5 ATOS',
            'SUBIR GPM - AJUSTAR ORIGEM',
            'OFF - REGIÃO FORA DA COLETA',
            'SUBIR GPM - ACIMA DE 5 ATOS)',
            'GPM - FICHA IMPORTADA'
            
        ],
        default='OFF - DUPLICIDADES'
        )

    # Validação de GACode
    logger.write( etapa='processamento', mensagem=f'ref segmentação ajuste gacode para o time de qualidade amostral')
    df_ids_recrutados_origen_validacao['validacao_gacode'] = np.select(
        [
            df_ids_recrutados_origen_validacao['GACODE_KANTAR_Nuevo'] == df_ids_recrutados_origen_validacao['Gacode'],
            df_ids_recrutados_origen_validacao['GACODE_KANTAR_Nuevo'] != df_ids_recrutados_origen_validacao['Gacode'],
            df_ids_recrutados_origen_validacao['Gacode'].isna()
                    
        ],
        [
            'CORRETO',
            'AJUSTAR MANUAL',
            'FICHA SEM GACODE'
        ],
        default=None
    )

    logger.write( etapa='processamento', mensagem=f'ref decisão origem opicioanis são sempre pharma')

    df_ids_recrutados_origen_validacao['Origem_importar'] = np.select(
        [
            df_ids_recrutados_origen_validacao['Pre_Origen'].eq(
                df_ids_recrutados_origen_validacao['Origen_Recrutado_32_IHS']
            ),

            df_ids_recrutados_origen_validacao['Pre_Origen'].eq(
                df_ids_recrutados_origen_validacao['Origen_Recrutado_42_Expansao']
            ),

            df_ids_recrutados_origen_validacao[
                ['Origen_Recrutado_32_IHS',
                'Origen_Recrutado_42_Expansao']
            ].isna().all(axis=1)
        ],
        [
            df_ids_recrutados_origen_validacao['Origen_Recrutado_32_IHS'],
            df_ids_recrutados_origen_validacao['Origen_Recrutado_42_Expansao'],
            'FORA DA COLETA'
        ],
        default=df_ids_recrutados_origen_validacao['Origen_Recrutado_42_Expansao'] # Origem Padrão
    )

    logger.write( etapa='processamento', mensagem=f'ref segmentacao monoindividuo & nse')
    df_ids_recrutados_origen_validacao['Classific'] = np.select(
    [
        (df_ids_recrutados_origen_validacao['Classe'] == 6) & (df_ids_recrutados_origen_validacao['P12a#1'] == 1),
        (df_ids_recrutados_origen_validacao['Classe'] == 6),  
        (df_ids_recrutados_origen_validacao['P12a#1'] == 1)
                    
    ],
    [
        'MONO_INDIV&NSE_DE',
        'NSE_DE',
        'MONO_INDIV'
    ],
    default= None
    )



    return df_ids_recrutados_origen_validacao