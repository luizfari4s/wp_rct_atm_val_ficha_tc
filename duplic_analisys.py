import process
from process import logger
import numpy as np
import pandas as pd

def analise_duplicidade_e_crterio(vl_atos_recrutamento_trat,vl_atos_recrutamento_criterio,vl_atos_recrutamento_vivos,df_mortalidade):

    logger.write( etapa='processamento', mensagem=f'ref normalização')

    # Normalização
    vl_atos_recrutamento_trat = process.tel_number_pdr_val(vl_atos_recrutamento_trat, 'P10e#2_t')
    vl_atos_recrutamento_trat = process.email_pdr_val(vl_atos_recrutamento_trat, 'P10d_t')
    
    logger.write( etapa='processamento', mensagem=f'ref analise duplicidade')
    # Contagem de ocorrências
    vl_atos_recrutamento_dpl_em = vl_atos_recrutamento_trat.groupby('Email_NRZD')['PanelSmart#1.1'].count().reset_index().sort_values(by='PanelSmart#1.1',ascending= False)
    vl_atos_recrutamento_dpl_tl = vl_atos_recrutamento_trat.groupby('Telefone_NRZD')['PanelSmart#1.1'].count().reset_index().sort_values(by='PanelSmart#1.1', ascending= False)

    logger.write( etapa='processamento', mensagem=f'ref atribuição duplicidade')
    # Atribuição de duplicidade
    vl_atos_recrutamento_dpl_em['Duplicidade_de_Email'] = vl_atos_recrutamento_dpl_em['PanelSmart#1.1'] > 1
    vl_atos_recrutamento_dpl_tl['Duplicidade_de_Telefone'] = vl_atos_recrutamento_dpl_tl['PanelSmart#1.1'] > 1

    logger.write( etapa='processamento', mensagem=f'ref cruzamento principal')
    # Cruzamento com base principal
    mrg_em = vl_atos_recrutamento_trat.merge(vl_atos_recrutamento_dpl_em[['Email_NRZD','Duplicidade_de_Email']],on='Email_NRZD', how = 'left')
    mrg_tl = mrg_em.merge(vl_atos_recrutamento_dpl_tl[['Telefone_NRZD','Duplicidade_de_Telefone']],on='Telefone_NRZD', how = 'left')

    logger.write( etapa='processamento', mensagem=f'ref cruzamento principal')
    # Validação
    print('***REVISÃO ENTRADA*** \ntrat: ',vl_atos_recrutamento_trat.shape[0])
    print('tl: ',vl_atos_recrutamento_dpl_tl.shape[0])
    print('em: ',vl_atos_recrutamento_dpl_em.shape[0])

    logger.write( etapa='processamento', mensagem=f'ref faixas de atos (bins) e os rótulos de análise')
    # Definir os limites das faixas (bins) e os rótulos correspondentes
    bins = [0, 4, 9, 14, 19, 24, float('inf')]
    labels = ['1 a 4 atos', '5 a 9 atos', '10 a 14 atos', '15 a 19 atos', '20 a 24 atos', '25+ atos']

    aux = vl_atos_recrutamento_criterio.groupby(['UserPS']).agg(
        ultima_trasmissao = ('DiaDeCompra', 'max'),
        NumCompras = ('NumCompras','sum')
    ).reset_index()

    aux['FaixaNumCompras'] = pd.cut(aux['NumCompras'], bins=bins, labels=labels, right=True)
    mrg_tl['PanelSmart#1'] = mrg_tl['PanelSmart#1'].astype(str)

    logger.write( etapa='processamento', mensagem=f'ref base de retorno vl_atos_recrutamento (passagem)')
    vl_atos = mrg_tl.merge(aux, left_on = 'PanelSmart#1',right_on='UserPS', how='left')
    # Geração base atos recrutamento
 
    vl_atos_recrutamento = (
        vl_atos
        .merge(
            vl_atos_recrutamento_vivos[['iddomicilio', 'Data_Entrada','Origen Proveedor']], # Ajuste 14/07/2026: Base direto do GPM (todos os vivos)
            left_on='PanelSmart#1',
            right_on='iddomicilio',
            how='outer',
            indicator=True
        )
        .copy()
    )
    # Fast normalization
    vl_atos_recrutamento['PanelSmart#1'] = vl_atos_recrutamento['PanelSmart#1'].fillna(vl_atos_recrutamento['iddomicilio'])
    vl_atos_recrutamento['iddomicilio'] = vl_atos_recrutamento['iddomicilio'].fillna(vl_atos_recrutamento['PanelSmart#1'])

    logger.write( etapa='processamento', mensagem=f'ref obtensão dos dados de mortalidade')

    
    df_mortalidade['PanelSmart#1'] = df_mortalidade['PanelSmart#1'].astype(str)
    vl_atos_recrutamento = vl_atos_recrutamento.merge(df_mortalidade[['PanelSmart#1','FSPanel1']], on = 'PanelSmart#1', how='left')

    return vl_atos_recrutamento

def analise_segmentacao_atos(vl_atos_recrutamento):

    logger.write( etapa='processamento', mensagem=f'ref carregaameto dos atos recrutamento')

    sem_dup_email = vl_atos_recrutamento['Duplicidade_de_Email'].eq(False)
    sem_dup_tel = vl_atos_recrutamento['Duplicidade_de_Telefone'].eq(False)

    cond_base = sem_dup_email & sem_dup_tel

    logger.write( etapa='processamento', mensagem=f'ref criterio de comportamento exceão perfil aplicação')
    condicoes_ok = [
        cond_base & vl_atos_recrutamento['FaixaNumCompras'].eq('25+ atos'),
        cond_base & vl_atos_recrutamento['NumCompras'].ge(15) & vl_atos_recrutamento['Classe'].eq(6),
        cond_base & vl_atos_recrutamento['P12a#1'].eq(1) & vl_atos_recrutamento['NumCompras'].ge(15),
    ]

    saidas_ok = [
        'OK_25_ATOS',
        'OK_15_COMPRAS_CLASSE_6',
        'OK_P12A_15_COMPRAS',
    ]

    vl_atos_recrutamento['saida_decisao'] = np.select(
        condicoes_ok,
        saidas_ok,
        default='AGUARDAR'
    )

    motivos = []

    logger.write( etapa='processamento', mensagem=f'ref criterio de qualidade aplicação')
    motivos.append(np.where(vl_atos_recrutamento['Duplicidade_de_Email'].eq(True), 'EMAIL_DUPLICADO', ''))
    motivos.append(np.where(vl_atos_recrutamento['Duplicidade_de_Telefone'].eq(True), 'TELEFONE_DUPLICADO', ''))

    cumpre_criterio_qualidade = (
        vl_atos_recrutamento['FaixaNumCompras'].eq('25+ atos') |
        (vl_atos_recrutamento['NumCompras'].ge(15) & vl_atos_recrutamento['Classe'].eq(6)) |
        (vl_atos_recrutamento['P12a#1'].eq(1) & vl_atos_recrutamento['NumCompras'].ge(15))
    )

    motivos.append(np.where(~cumpre_criterio_qualidade, 'NAO_CUMPRE_CRITERIO_QUALIDADE', ''))

    vl_atos_recrutamento['flag_complementar'] = (
        pd.DataFrame(motivos).T
        .apply(lambda x: ' | '.join([i for i in x if i]), axis=1)
    )

    vl_atos_recrutamento.loc[vl_atos_recrutamento['saida_decisao'] != 'AGUARDAR', 'flag_complementar'] = ''

    return vl_atos_recrutamento





