import charge
import duplic_analisys
import origen_analisys
import controle_lotes
import output
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from wp_rct_atm_atos_tc.main import main as atualizar_atos

def main():

    # Projeto paralelo wp_rct_atm_atos_tc
    atualizar_atos(None)
    
    df_periodo,df_trat,df_ficha,df_vivos,df_vivos_geral,df_origem_id,df_gacode,df_criterio,df_ls_batch,pst_egj,pst_out,df_mortalidade = charge.carregar_dados()

    vl_atos_recrutamento = duplic_analisys.analise_duplicidade_e_crterio(df_trat,df_criterio,df_vivos,df_mortalidade)
    vl_atos_recrutamento = duplic_analisys.analise_segmentacao_atos(vl_atos_recrutamento)


    df_ids_recrutados_origen_validacao = origen_analisys.origen_analisys(vl_atos_recrutamento, df_gacode,df_origem_id)
    df_ids_recrutados_origen_validacao = origen_analisys.analise_segmentacao_origens(df_ids_recrutados_origen_validacao)


    df_rct_batch_vivos_pend_importacao = controle_lotes.controle_lotes(df_ids_recrutados_origen_validacao,df_ls_batch,df_periodo,df_vivos_geral)

    output.arquivos_de_saida(df_rct_batch_vivos_pend_importacao,df_ficha,df_periodo,pst_egj,pst_out)

if __name__ == "__main__":
    main()