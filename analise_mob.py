"""
Análise completa do movimento de mobs no Minecraft
Lei difusiva, incertezas, barras de erro e gráfico log-log
"""

import seaborn as sns
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.optimize import curve_fit

# ============================================
# 1. CONFIGURAÇÕES GLOBAIS
# ============================================

# Configurar estilo dos gráficos (opcional)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 10

# Parâmetros ajustáveis
NOME_ARQUIVO = 'dados_mob.txt'  # ← MUDE PARA O NOME DO SEU ARQUIVO
WINDOW_SIZE = 60  # janela de tempo para médias (segundos) - AJUSTE SE QUISER

# Habilitar uso limpo de LaTeX/mathText no Matplotlib
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.family'] = 'STIXGeneral'

# ============================================
# 2. CARREGAR OS DADOS
# ============================================

print("=" * 60)
print("ANÁLISE DO MOVIMENTO DE MOBS NO MINECRAFT")
print("=" * 60)

try:
    df = pd.read_csv(NOME_ARQUIVO, sep=',', skipinitialspace=True)
    print(f"\n✓ Arquivo '{NOME_ARQUIVO}' carregado com sucesso.")
except FileNotFoundError:
    print(f"\n✗ ERRO: Arquivo '{NOME_ARQUIVO}' não encontrado.")
    print("  Verifique se o arquivo está na mesma pasta que este script.")
    print(f"  Ou altere a variável NOME_ARQUIVO no código.")
    exit()

# Verificar colunas
colunas_esperadas = ['tick', 'pos_x', 'pos_y', 'pos_z']
for col in colunas_esperadas:
    if col not in df.columns:
        print(f"\n✗ ERRO: Coluna '{col}' não encontrada no arquivo.")
        print(f"  Colunas disponíveis: {list(df.columns)}")
        exit()

print(f"  Total de pontos coletados: {len(df)}")

# ============================================
# 3. PRÉ-PROCESSAMENTO
# ============================================

# Converter ticks para segundos (20 ticks = 1 segundo)
df['tempo_seg'] = df['tick'] / 20.0

# Posição inicial (primeiro ponto)
x0 = df['pos_x'].iloc[0]
z0 = df['pos_z'].iloc[0]

# Deslocamento em relação à origem
df['desloc_x'] = df['pos_x'] - x0
df['desloc_z'] = df['pos_z'] - z0

# Distância da origem e seu quadrado
df['r'] = np.sqrt(df['desloc_x']**2 + df['desloc_z']**2)
df['r2'] = df['r']**2

# Passos (variação entre pontos consecutivos)
df['dx'] = df['pos_x'].diff()
df['dz'] = df['pos_z'].diff()
df['passo'] = np.sqrt(df['dx']**2 + df['dz']**2)

# ============================================
# 4. ESTATÍSTICAS DOS PASSOS
# ============================================

passos_validos = df['passo'].dropna()
passos_validos = passos_validos[passos_validos > 0]  # remove pausas

print("\n" + "=" * 60)
print("ESTATÍSTICAS DOS PASSOS")
print("=" * 60)
print(f"  Média do passo: {passos_validos.mean():.4f} blocos")
print(f"  Mediana do passo: {passos_validos.median():.4f} blocos")
print(f"  Desvio padrão: {passos_validos.std():.4f} blocos")
print(f"  Número total de passos: {len(passos_validos)}")

# ============================================
# 5. ANÁLISE TEMPORAL (PAUSAS)
# ============================================

# Identificar quando o mob está parado (passo = 0 ou NaN)
df['parado'] = (df['passo'] == 0) | (df['passo'].isna())

# Calcular tempo de coleta (assumindo intervalo constante entre ticks)
dt = df['tempo_seg'].diff().median() if len(df) > 1 else 0.05  # tipicamente 0.05s
tempo_total = df['tempo_seg'].iloc[-1] - df['tempo_seg'].iloc[0]
tempo_parado = df[df['parado']]['tempo_seg'].count() * dt
tempo_movimento = tempo_total - tempo_parado
fracao_parado = tempo_parado / tempo_total if tempo_total > 0 else 0

print("\n" + "=" * 60)
print("ANÁLISE TEMPORAL")
print("=" * 60)
print(f"  Tempo total de coleta: {tempo_total:.1f} s ({tempo_total/60:.1f} min)")
print(f"  Tempo efetivo em movimento: {tempo_movimento:.1f} s")
print(f"  Fração do tempo parado: {fracao_parado:.1%}")

# ============================================
# 6. MÉDIAS POR JANELA PARA REGRESSÃO
# ============================================

# Definir janelas de tempo
df['tempo_bin'] = (df['tempo_seg'] // WINDOW_SIZE) * WINDOW_SIZE

# Calcular média, desvio padrão e erro padrão do r² em cada janela
estatisticas = df.groupby('tempo_bin')['r2'].agg(['mean', 'std', 'count']).reset_index()
estatisticas.columns = ['tempo', 'r2_mean', 'r2_std', 'n']
estatisticas['r2_sem'] = estatisticas['r2_std'] / np.sqrt(estatisticas['n'])  # erro padrão

# Remover janelas com poucos pontos (mínimo 5)
estatisticas = estatisticas[estatisticas['n'] >= 5].copy()

print(f"\n  Janelas de tempo: {WINDOW_SIZE} s")
print(f"  Número de janelas válidas: {len(estatisticas)}")

# ============================================
# 7. REGRESSÃO LINEAR PONDERADA (COM INCERTEZAS)
# ============================================

x = estatisticas['tempo'].values
y = estatisticas['r2_mean'].values
y_err = estatisticas['r2_sem'].values

# Pesos = 1/σ² (evitar divisão por zero com epsilon)
pesos = 1 / (y_err**2 + 1e-10)

# Regressão linear ponderada manual
A = np.vstack([x, np.ones(len(x))]).T
W = np.diag(pesos)

try:
    coef = np.linalg.inv(A.T @ W @ A) @ (A.T @ W @ y)
    slope, intercept = coef
    
    # Calcular erros dos coeficientes
    y_pred = slope * x + intercept
    residuals = y - y_pred
    sigma_sq = np.sum(pesos * residuals**2) / (len(x) - 2)
    cov_matrix = sigma_sq * np.linalg.inv(A.T @ W @ A)
    slope_err = np.sqrt(cov_matrix[0, 0])
    intercept_err = np.sqrt(cov_matrix[1, 1])
    
    # Calcular R² ponderado
    y_mean_weighted = np.average(y, weights=pesos)
    ss_res = np.sum(pesos * residuals**2)
    ss_tot = np.sum(pesos * (y - y_mean_weighted)**2)
    r2_weighted = 1 - ss_res / ss_tot
    
    print("\n" + "=" * 60)
    print("REGRESSÃO LINEAR PONDERADA")
    print("=" * 60)
    print(f"  Coeficiente de difusão D = {slope:.3f} ± {slope_err:.3f} blocos²/s")
    print(f"  Intervalo de confiança 95%: [{slope - 1.96*slope_err:.3f}, {slope + 1.96*slope_err:.3f}]")
    print(f"  Intercepto: {intercept:.1f} ± {intercept_err:.1f} blocos²")
    print(f"  R² ponderado: {r2_weighted:.4f}")
    
except np.linalg.LinAlgError:
    print("\n✗ ERRO na regressão ponderada. Usando regressão simples.")
    slope, intercept, r_value, p_value, slope_err = stats.linregress(x, y)[:5]
    r2_weighted = r_value**2
    print(f"  Coeficiente de difusão D = {slope:.3f} ± {slope_err:.3f} blocos²/s")
    print(f"  R²: {r2_weighted:.4f}")

# ============================================
# 8. GRÁFICO 1: TRAJETÓRIA
# ============================================

plt.figure(figsize=(8, 8))
plt.plot(df['desloc_x'], df['desloc_z'], 'b-', linewidth=0.8, alpha=0.6)
plt.plot(df['desloc_x'].iloc[0], df['desloc_z'].iloc[0], 'go', markersize=10, label='Início')
plt.plot(df['desloc_x'].iloc[-1], df['desloc_z'].iloc[-1], 'ro', markersize=10, label='Fim')
plt.xlabel('Deslocamento x (blocos)')
plt.ylabel('Deslocamento z (blocos)')
plt.title('Trajetória do mob no plano horizontal')
plt.legend()
plt.grid(True, alpha=0.3)
plt.axis('equal')
plt.tight_layout()
plt.savefig('01_trajetoria_mob.png', dpi=150)
plt.close()
print("\n✓ Gráfico salvo: 01_trajetoria_mob.png")

# ============================================
# 9. GRÁFICO 2: r² vs TEMPO COM BARRAS DE ERRO (VERSÃO FINAL)
# ============================================

# Calcular o erro típico (para mostrar no gráfico)
erro_medio = estatisticas['r2_sem'].mean()
erro_mediano = estatisticas['r2_sem'].median()

plt.figure(figsize=(12, 8))

# Dados brutos (opcional, bem transparente)
plt.plot(df['tempo_seg'], df['r2'], 'b.', alpha=0.05, markersize=1, label='Dados brutos (cada ponto)')

# Médias por janela com barras de erro (com LaTeX)
plt.errorbar(estatisticas['tempo'], estatisticas['r2_mean'],
             yerr=estatisticas['r2_sem'],
             fmt='ro', markersize=4, capsize=3, capthick=1,
             label=f'Médias a cada {WINDOW_SIZE} s (erro típico: $\pm$ {erro_medio:.1f} $\mathrm{{blocos}}^2$)')

# Reta do ajuste ponderado (com LaTeX)
x_line = np.array([0, estatisticas['tempo'].max()])
y_line = slope * x_line + intercept
plt.plot(x_line, y_line, 'k-', linewidth=2,
         label=f'Ajuste linear: $D = {slope:.2f} \pm {slope_err:.2f}\ \mathrm{{blocos}}^2/\mathrm{{s}}$')

plt.xlabel('Tempo, $t$ (s)', fontsize=12)
plt.ylabel(r'$\langle r^2 \rangle \quad (\mathrm{blocos}^2)$', fontsize=12)

plt.title('Desvio quadrático médio em função do tempo', fontsize=14)
plt.legend(loc='upper left', fontsize=10)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('02_r2_vs_tempo_com_erros.png', dpi=200)
plt.close()
print(f"✓ Gráfico salvo: 02_r2_vs_tempo_com_erros.png")
print(f"  Erro típico das médias: ± {erro_medio:.2f} blocos² (mediana: ± {erro_mediano:.2f})")

# ============================================
# 10. HISTOGRAMA DOS PASSOS: COMPLETO vs FILTRADO
# ============================================

import seaborn as sns
from scipy.stats import skew

# Configurar estilo
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.1)

# Definir limiar de filtro
LIMIAR = 0.75
passos_filtrados = passos_validos[passos_validos > LIMIAR]

# Calcular estatísticas
skew_original = skew(passos_validos)
skew_filtrado = skew(passos_filtrados)

print(f"\n=== COMPARAÇÃO DOS PASSOS ===")
print(f"  Limiar de filtro: ℓ > {LIMIAR} blocos")
print(f"  Passos totais: {len(passos_validos)}")
print(f"  Passos mantidos: {len(passos_filtrados)} ({100*len(passos_filtrados)/len(passos_validos):.1f}%)")
print(f"  Skewness original: {skew_original:.2f}")
print(f"  Skewness filtrado: {skew_filtrado:.2f}")

# Criar figura com dois subplots lado a lado
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# ===== FIGURA A: Dados completos (sem filtro) =====
sns.histplot(passos_validos, bins=50, kde=True, stat='density',
             color='steelblue', alpha=0.6, edgecolor='black', linewidth=0.5, ax=ax1)
ax1.axvline(passos_validos.mean(), color='r', linestyle='--', linewidth=2,
            label=f'Média = {passos_validos.mean():.3f}')
ax1.axvline(passos_validos.median(), color='g', linestyle='--', linewidth=2,
            label=f'Mediana = {passos_validos.median():.3f}')
ax1.text(0.95, 0.95, f'Skewness = {skew_original:.2f}\n(assimetria negativa)',
         transform=ax1.transAxes, fontsize=9,
         verticalalignment='top', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
ax1.set_xlabel('Comprimento do passo (blocos)', fontsize=11)
ax1.set_ylabel('Densidade de probabilidade', fontsize=11)
ax1.set_title('(a) Distribuição completa\n(todos os passos)', fontsize=12)
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# ===== FIGURA B: Dados filtrados (ℓ > limiar) =====
sns.histplot(passos_filtrados, bins=30, kde=True, stat='density',
             color='steelblue', alpha=0.6, edgecolor='black', linewidth=0.5, ax=ax2)
ax2.axvline(passos_filtrados.mean(), color='r', linestyle='--', linewidth=2,
            label=f'Média = {passos_filtrados.mean():.3f}')
ax2.axvline(passos_filtrados.median(), color='g', linestyle='--', linewidth=2,
            label=f'Mediana = {passos_filtrados.median():.3f}')
ax2.text(0.95, 0.95, f'Skewness = {skew_filtrado:.2f}\nFiltro: ℓ > {LIMIAR}',
         transform=ax2.transAxes, fontsize=9,
         verticalalignment='top', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
ax2.set_xlabel('Comprimento do passo (blocos)', fontsize=11)
ax2.set_ylabel('Densidade de probabilidade', fontsize=11)
ax2.set_title(f'(b) Passos significativos\n(ℓ > {LIMIAR} blocos)', fontsize=12)
ax2.legend(loc='upper left')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('03_histograma_passos_comparacao.png', dpi=150)
plt.close()
print("✓ Gráfico salvo: 03_histograma_passos_comparacao.png (comparação lado a lado)")

# ============================================
# 11. GRÁFICO LOG-LOG - VERSÃO QUE FUNCIONAVA (SÓ LIMPEZA MÍNIMA)
# ============================================

print("\n" + "=" * 60)
print("GERANDO GRÁFICO LOG-LOG")
print("=" * 60)

# Verificar dados disponíveis
print(f"  Janelas disponiveis: {len(estatisticas)}")
print(f"  Faixa de r2_mean: [{estatisticas['r2_mean'].min():.2f}, {estatisticas['r2_mean'].max():.2f}]")

# Filtrar apenas valores positivos e razoáveis
log_data = estatisticas[estatisticas['r2_mean'] > 0.5].copy()
print(f"  Apos filtro (r2_mean > 0.5): {len(log_data)} janelas")

if len(log_data) >= 3:
    # Calcular logaritmos manualmente com protecao
    log_t = []
    log_r2 = []
    log_r2_err = []
    
    for _, row in log_data.iterrows():
        t = row['tempo']
        r2 = row['r2_mean']
        r2_err = row['r2_sem']
        
        # Evitar log de valores nao positivos
        if t <= 0 or r2 <= 0:
            continue
            
        log_t_val = np.log10(t)
        log_r2_val = np.log10(r2)
        
        # Propagacao de erro
        if r2 > 0 and r2_err > 0:
            log_r2_err_val = r2_err / (r2 * np.log(10))
        else:
            log_r2_err_val = 0.01
        
        log_t.append(log_t_val)
        log_r2.append(log_r2_val)
        log_r2_err.append(log_r2_err_val)
    
    if len(log_t) >= 3:
        # Converter para arrays numpy
        log_t = np.array(log_t)
        log_r2 = np.array(log_r2)
        log_r2_err = np.array(log_r2_err)
        
        print(f"  Pontos validos para log-log: {len(log_t)}")
        
        # Regressao linear
        slope_log, intercept_log, r_value_log, p_value_log, std_err_log = stats.linregress(log_t, log_r2)
        
        print(f"\n  Expoente alpha = {slope_log:.4f} ± {std_err_log:.4f}")
        print(f"  R² do ajuste: {r_value_log**2:.4f}")
        
        # Criar figura
        plt.figure(figsize=(10, 8))
        
        # Pontos com barras de erro (VERMELHOS)
        plt.errorbar(log_t, log_r2,
                     yerr=log_r2_err,
                     fmt='ro', markersize=5, capsize=3, capthick=1,
                     label='Dados experimentais (medias por janela)')
        
        # Reta de ajuste (com LaTeX)
        x_line = np.array([log_t.min(), log_t.max()])
        y_line = slope_log * x_line + intercept_log
        plt.plot(x_line, y_line, 'k-', linewidth=2,
                 label=r'Ajuste: $\langle r^2 \rangle \propto t^{%.3f \pm %.3f}$' % (slope_log, std_err_log))
        
        # Referência: difusão normal (com LaTeX)
        y_ref = 1 * x_line + intercept_log
        plt.plot(x_line, y_ref, 'b--', linewidth=1.5, alpha=0.7,
                 label=r'Difusão normal ($\alpha = 1$)')
        
        # RÓTULOS (em formato LaTeX para artigo)
        plt.xlabel(r'$\log_{10}(t / \mathrm{s})$', fontsize=12)
        plt.ylabel(r'$\log_{10}(\langle r^2 \rangle / \mathrm{blocos}^2)$', fontsize=12)
        plt.title('Análise de escala log-log — Expoente de difusão', fontsize=14)
        
        # Legenda
        plt.legend(loc='upper left', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('04_loglog_r2_vs_tempo.png', dpi=200)
        plt.close()
        print("✓ Grafico salvo: 04_loglog_r2_vs_tempo.png")
        
    else:
        print(f"  ERRO: Apenas {len(log_t)} pontos apos limpeza (minimo 3)")
else:
    print(f"  ERRO: Apenas {len(log_data)} janelas com r2_mean > 0.5 (minimo 3)")

# ============================================
# 12. SALVAR RESULTADOS
# ============================================

# Salvar dados processados
df.to_csv('dados_processados.csv', index=False)
print("\n✓ Dados processados salvos: dados_processados.csv")

# Salvar estatísticas das janelas
estatisticas.to_csv('estatisticas_janelas.csv', index=False)
print("✓ Estatísticas das janelas salvas: estatisticas_janelas.csv")

# Criar um arquivo de resumo
with open('resul_analise.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 60 + "\n")
    f.write("ANÁLISE DO MOVIMENTO DE MOBS NO MINECRAFT\n")
    f.write("=" * 60 + "\n\n")
    
    f.write(f"Total de pontos coletados: {len(df)}\n")
    f.write(f"Tempo total de coleta: {tempo_total:.1f} s ({tempo_total/60:.1f} min)\n")
    f.write(f"Fração do tempo parado: {fracao_parado:.1%}\n\n")
    
    f.write("Estatística dos passos:\n")
    f.write(f"  Média: {passos_validos.mean():.4f} blocos\n")
    f.write(f"  Mediana: {passos_validos.median():.4f} blocos\n")
    f.write(f"  Desvio padrão: {passos_validos.std():.4f} blocos\n\n")
    
    f.write("Regressão linear (lei difusiva):\n")
    f.write(f"  D = {slope:.3f} ± {slope_err:.3f} blocos²/s\n")
    f.write(f"  R² ponderado = {r2_weighted:.4f}\n\n")
    
    if len(log_data) >= 3:
        f.write("Análise log-log:\n")
        f.write(f"  α = {slope_log:.4f} ± {std_err_log:.4f}\n")

print("✓ Resumo salvo: resul_analise.txt")

print("\n" + "=" * 60)
print("ANÁLISE CONCLUÍDA COM SUCESSO!")
print("=" * 60)
print("\nArquivos gerados:")
print("  - 01_trajetoria_mob.png")
print("  - 02_r2_vs_tempo_com_erros.png")
print("  - 03_histograma_passos.png")
print("  - 04_loglog_r2_vs_tempo.png (se aplicável)")
print("  - dados_processados.csv")
print("  - estatisticas_janelas.csv")
print("  - resul_analise.txt")