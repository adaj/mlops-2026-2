"""Figuras 12, 13 e 14 do apêndice "Data storytelling em monitoramento de sistemas de ML".

Uso:  python apendice_figuras.py   (gera os PNGs na pasta deste script)

Todas as figuras têm 6 polegadas de largura (= 432 pt, a largura da figura no documento),
então o tamanho de fonte em pt no código é o tamanho impresso. Mínimo: 9 pt, exceto o
painel "Opções padrão" da Figura 12, cuja fonte minúscula é proposital (imita um print reduzido).

Dados sintéticos com o formato da rodada 4 (20/11/2026): fase estável 11:20-11:24 com todos
os PSI < 0,1; português 11:24-11:28; PSI do comprimento passa de 0,25 às 11:24:45 e termina
em 2,82; PSI finais 3 classes 2,82 / 0,32 / 0,31 e 7 classes 2,82 / 3,80 / 0,04; depois das
11:28 não há tráfego e as séries ficam retas.
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch

AQUI = Path(__file__).resolve().parent
ITALICO = fm.FontProperties(fname=str(AQUI / "fonts" / "CrimsonPro-Italic.ttf"))

plt.rcParams.update({"font.family": "Inter", "font.size": 10, "axes.titlesize": 11,
                     "svg.fonttype": "none"})
DPI = 300
# Paleta das figuras do capítulo (diagramas.py / build_figures.py)
PET, PET_CLARO = "#0E7C7B", "#8FD1CF"
CINZA, CINZA_ESC, CINZA_REF = "#BDBDBD", "#6E6E6E", "#8A8A8A"
FAIXA = "#EFEFEF"
VERM, LARANJA, NORMAL = "#C4162A", "#FF9830", "#DDDDDD"
TXT = "#222222"

# ------------------------------------------------------------------ dados (passo de 15 s)
T = np.arange(0, 41) * 15 / 60 + 19.5          # minutos depois das 11:00: 11:19:30 a 11:29:30
FIM_ESTAVEL, FIM_PT = 24.0, 28.0
rng = np.random.default_rng(20261120)


def serie(rampa, final):
    """Ruído < 0,1 até 11:24; rampa (valores a partir de 11:24:15); oscila; reta depois de 11:28."""
    y = np.clip(0.035 + rng.normal(0, 0.02, len(T)), 0.004, 0.092)
    i0 = int(np.where(np.isclose(T, 24.25))[0][0])
    i_fim = int(np.where(np.isclose(T, FIM_PT))[0][0])
    for k, v in enumerate(rampa):
        y[i0 + k] = v
    j = i0 + len(rampa)
    while j < i_fim:
        y[j] = final * (1 + rng.normal(0, 0.018))
        j += 1
    y[i_fim:] = final
    return y


COMP = serie([0.08, 0.17, 0.42, 0.68, 1.00, 1.30, 1.68, 1.93, 2.42, 2.80, 2.81, 2.72, 2.77, 2.93], 2.82)
C7 = serie([0.06, 0.11, 0.17, 0.24, 0.38, 0.57, 0.77, 1.10, 2.05, 3.75, 3.75, 3.76, 3.77], 3.80)
CL3 = serie([0.04, 0.05, 0.07, 0.09, 0.11, 0.15, 0.18, 0.22, 0.27, 0.38, 0.41, 0.40, 0.37], 0.32)
CF3 = serie([0.03, 0.05, 0.06, 0.08, 0.10, 0.13, 0.17, 0.21, 0.26, 0.33, 0.34, 0.33, 0.34], 0.31)
CF7 = serie([0.02, 0.02, 0.03, 0.03, 0.02, 0.03, 0.04, 0.03, 0.03, 0.04, 0.03, 0.04, 0.03], 0.04)
COMP7 = COMP.copy()                               # mesma variável de entrada nos dois modelos
assert max(s[T < FIM_ESTAVEL].max() for s in (COMP, C7, CL3, CF3, CF7)) < 0.1
assert COMP[np.isclose(T, 24.5)][0] < 0.25 < COMP[np.isclose(T, 24.75)][0]


def hhmm(m):
    return f"11:{int(m):02d}"


def limpa(ax, cor=CINZA):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(cor)
    ax.tick_params(colors=CINZA_ESC, length=3, width=0.8)


def seta(ax, a, b, cor=CINZA_ESC, lw=1.1, **kw):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9, lw=lw, color=cor,
                                 shrinkA=0, shrinkB=1.5, **kw))


# =================================================================== Figura 12: antes e depois
def figura12():
    fig = plt.figure(figsize=(6.0, 3.55), dpi=DPI)
    W, H = 6.0, 3.55

    def caixa(x, y, w, h):          # polegadas -> fração da figura
        return [x / W, y / H, w / W, h / H]

    # títulos
    fig.text(0.06 / W, 3.40 / H, "Opções padrão", ha="left", va="center", fontsize=12, weight="semibold", color=TXT)
    fig.text(0.06 / W, 3.19 / H, "o painel como o Grafana o monta", ha="left", va="center", fontsize=9, color=CINZA_ESC)
    fig.text(3.14 / W, 3.40 / H, "Painel preparado", ha="left", va="center", fontsize=12, weight="semibold", color=TXT)
    fig.text(3.14 / W, 3.19 / H, "mesmos dados, uma pergunta", ha="left", va="center", fontsize=9, color=CINZA_ESC)

    # ---------------- Antes: painel do Grafana (tema claro, padrões de fábrica), reduzido
    moldura = fig.add_axes(caixa(0.04, 0.04, 2.86, 3.0)); moldura.axis("off")
    moldura.add_patch(FancyBboxPatch((0.004, 0.004), 0.992, 0.992, boxstyle="round,pad=0,rounding_size=0.012",
                                     transform=moldura.transAxes, fc="white", ec="#D8D9DA", lw=0.8))
    G_TXT, G_GRADE = "#464C54", "#E6E6E6"
    fs = 5.6
    moldura.text(0.035, 0.955, "drift_psi", transform=moldura.transAxes, fontsize=6.4, weight="semibold",
                 color=G_TXT, va="center")
    moldura.text(0.965, 0.955, "⋮", transform=moldura.transAxes, fontsize=7, color="#8E8E8E",
                 va="center", ha="right", family="DejaVu Sans")
    ax = fig.add_axes(caixa(0.30, 1.28, 2.50, 1.52))
    grafana = ["#73BF69", "#F2CC0C", "#5794F2", "#FF9830", "#F2495C", "#B877D9"]
    m3, m7 = 'model="confusion-clf"', 'model="clair_intents-clf"'
    series = [  # ordem do Prometheus, não a do texto
        ('feature="confidence"', m7, CF7), ('feature="input_words"', m3, COMP),
        ('feature="predicted_intent"', m7, C7), ('feature="confidence"', m3, CF3),
        ('feature="input_words"', m7, COMP7), ('feature="predicted_intent"', m3, CL3),
    ]
    for (f, m, y), c in zip(series, grafana):
        ax.plot(T, y, color=c, lw=1.0)
    for x in (FIM_ESTAVEL, FIM_PT):     # anotações sem texto
        ax.axvline(x, color="#5794F2", lw=0.7, ls=(0, (3, 3)), alpha=0.8)
    ax.axhline(0.25, color="#F2495C", lw=0.6, ls=(0, (3, 3)))   # limiar sem rótulo
    ax.set_xlim(T[0], T[-1]); ax.set_ylim(0, 4.2)
    ax.set_xticks(np.arange(20, 30, 1)); ax.set_xticklabels([f"11:{m}:00" for m in range(20, 30)])
    ax.set_yticks([0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4])
    ax.set_yticklabels(["0", "0.5", "1", "1.5", "2", "2.5", "3", "3.5", "4"])
    ax.tick_params(labelsize=fs, colors=G_TXT, length=0, pad=2)
    ax.grid(color=G_GRADE, lw=0.5)
    for s in ax.spines.values():
        s.set_visible(False)
    for lab in ax.get_xticklabels():
        lab.set_rotation(0)
    # rótulos do eixo x se atropelam como no painel estreito; deixo um sim, um não como faz o Grafana
    for k, lab in enumerate(ax.get_xticklabels()):
        lab.set_visible(k % 2 == 0)
    # legenda em lista, nomes crus do Prometheus
    y0 = 0.98 / 3.0
    for k, ((f, m, _), c) in enumerate(zip(series, grafana)):
        yy = y0 - k * 0.046
        moldura.plot([0.035, 0.075], [yy, yy], transform=moldura.transAxes, color=c, lw=1.6,
                     solid_capstyle="round")
        moldura.text(0.09, yy, "drift_psi{" + f + ", " + m + "}", transform=moldura.transAxes,
                     fontsize=fs, color=G_TXT, va="center")

    # ---------------- Depois
    ax = fig.add_axes(caixa(3.53, 0.48, 2.36, 2.47))
    ax.axvspan(FIM_ESTAVEL, FIM_PT, color=FAIXA, lw=0, zorder=0)
    ax.text((FIM_ESTAVEL + FIM_PT) / 2, 4.42, "português", ha="center", va="center", fontsize=9.5,
            color=CINZA_ESC)
    for y in (CL3, CF3, CF7, C7):
        ax.plot(T, y, color=CINZA, lw=1.0, zorder=2, solid_capstyle="round")
    ax.axhline(0.25, color=VERM, lw=1.0, ls=(0, (4, 3)), zorder=3)
    ax.text(T[0] + 0.1, 0.36, "limiar de alerta\n(0,25)", fontsize=9, color=TXT, va="bottom", zorder=4,
            linespacing=1.1)
    ax.plot(T, COMP, color=PET, lw=2.4, zorder=5, solid_capstyle="round")
    ax.text(25.35, 1.72, "comprimento", fontsize=9.5, weight="semibold", color=TXT, ha="right", va="center")
    ax.text(26.25, 3.72, "classe prevista,\n7 classes", fontsize=9, color=CINZA_ESC, ha="right", va="center",
            linespacing=1.1)
    ax.text(T[-1] - 0.05, 0.42, "outras", fontsize=9, color=CINZA_ESC, ha="right", va="bottom")
    ax.set_xlim(T[0], T[-1]); ax.set_ylim(0, 4.6)
    ax.set_xticks([20, 22, 24, 26, 28]); ax.set_xticklabels([hhmm(m) for m in (20, 22, 24, 26, 28)])
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_ylabel("PSI", fontsize=10, color=TXT, labelpad=4)
    ax.tick_params(labelsize=9.5)
    ax.grid(axis="y", color="#EEEEEE", lw=0.8, zorder=0)
    limpa(ax)
    fig.savefig(AQUI / "fig12-antes-depois.png", dpi=DPI, facecolor="white")
    plt.close(fig)


# =================================================================== Figura 13: uma pergunta por painel
def figura13():
    W, H = 6.0, 4.1
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    perguntas = ["Há drift agora?", "Desde quando?", "Em qual variável\ne como?", "Alguém precisa\nagir?"]
    tipos = ["números e estados", "séries no tempo", None, "estado do alerta"]
    topo, alt, gap = 3.98, 0.86, 0.12
    X0 = 1.82                                   # início da coluna de painéis
    # seta de leitura
    yb = topo - 4 * alt - 3 * gap
    seta(ax, (0.12, topo - 0.10), (0.12, yb + 0.05), cor=CINZA, lw=1.3)
    for i, (p, t) in enumerate(zip(perguntas, tipos)):
        y1 = topo - i * (alt + gap); y0 = y1 - alt; yc = (y0 + y1) / 2
        ax.add_patch(Circle((0.40, y1 - 0.17), 0.12, fc=TXT, ec="none"))
        ax.text(0.40, y1 - 0.17, str(i + 1), ha="center", va="center", color="white", fontsize=9.5,
                weight="semibold")
        ax.text(0.60, y1 - 0.075, p, ha="left", va="top", fontsize=10.5,
                weight="semibold", color=TXT, linespacing=1.15)
        if t:
            ax.text(0.60, y0 + 0.06, t, ha="left", va="bottom", fontsize=9, color=CINZA_ESC)
        else:       # chave das barras: referência × atual
            for k, (nome, c) in enumerate((("referência", CINZA_REF), ("atual", PET))):
                yy = y0 + 0.30 - k * 0.20
                ax.add_patch(Rectangle((0.60, yy - 0.045), 0.12, 0.09, fc=c, ec="none"))
                ax.text(0.78, yy, nome, ha="left", va="center", fontsize=9, color=TXT)
        ax.plot([X0 - 0.10, W - 0.05], [y0 - gap / 2, y0 - gap / 2], color="#E4E4E4", lw=0.8) if i < 3 else None
        desenha_linha(ax, i, X0, y0 + 0.04, W - 0.06, y1 - 0.04)
    fig.savefig(AQUI / "fig13-uma-pergunta-por-painel.png", dpi=DPI, facecolor="white")
    plt.close(fig)


def painel(ax, x0, y0, x1, y1, titulo=None):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.05",
                                fc="white", ec="#CFCFCF", lw=0.8))
    if titulo:
        ax.text(x0 + 0.07, y1 - 0.07, titulo, ha="left", va="top", fontsize=9, color=TXT)


def mini_linha(ax, x0, y0, x1, y1, ys, ymax, destaque=None, cinzas=(), limiar=None, log=False):
    def px(t):
        return x0 + (t - T[0]) / (T[-1] - T[0]) * (x1 - x0)

    def py(v):
        return y0 + min(v, ymax) / ymax * (y1 - y0)
    ax.add_patch(Rectangle((px(FIM_ESTAVEL), y0), px(FIM_PT) - px(FIM_ESTAVEL), y1 - y0, fc=FAIXA, ec="none"))
    for s in cinzas:
        ax.plot(px(T), [py(v) for v in s], color=CINZA, lw=0.8)
    if limiar is not None:
        ax.plot([x0, x1], [py(limiar)] * 2, color=VERM, lw=0.8, ls=(0, (3, 2)))
    if destaque is not None:
        ax.plot(px(T), [py(v) for v in destaque], color=PET, lw=1.6)
    ax.plot([x0, x1], [y0, y0], color=CINZA, lw=0.7)


def mini_barras(ax, x0, y0, x1, y1, ref, atual, ymax):
    n = len(ref); w = (x1 - x0) / n
    for k, (r, a) in enumerate(zip(ref, atual)):
        bx = x0 + k * w
        ax.add_patch(Rectangle((bx + 0.12 * w, y0), 0.36 * w, r / ymax * (y1 - y0), fc=CINZA_REF, ec="none"))
        ax.add_patch(Rectangle((bx + 0.52 * w, y0), 0.36 * w, a / ymax * (y1 - y0), fc=PET, ec="none"))
    ax.plot([x0, x1], [y0, y0], color=CINZA, lw=0.7)


def desenha_linha(ax, i, X0, y0, X1, y1):
    wtot = X1 - X0
    if i == 0:      # três painéis de número
        gaps = 0.08; w = (wtot - 2 * gaps) / 3
        itens = [("comprimento", "2,82", PET, "PSI (limiar 0,25)"),
                 ("acima do limiar", "5 de 6", TXT, "instâncias"),
                 ("tráfego", "86", TXT, "mensagens/min")]
        for k, (tit, val, cor, sub) in enumerate(itens):
            a = X0 + k * (w + gaps)
            painel(ax, a, y0, a + w, y1, tit)
            ax.text(a + 0.07, y0 + 0.36, val, ha="left", va="center", fontsize=16, weight="semibold", color=cor)
            ax.text(a + 0.07, y0 + 0.07, sub, ha="left", va="bottom", fontsize=9, color=CINZA_ESC)
    elif i == 1:    # séries no tempo
        gaps = 0.08; w = (wtot - gaps) / 2
        painel(ax, X0, y0, X0 + w, y1, "PSI ao longo do tempo")
        mini_linha(ax, X0 + 0.10, y0 + 0.08, X0 + w - 0.10, y1 - 0.30, None, 4.2,
                   destaque=COMP, cinzas=(C7, CL3, CF3, CF7), limiar=0.25)
        a = X0 + w + gaps
        painel(ax, a, y0, X1, y1, "p-valor do KS (escala log)")
        lp = lambda s: -np.log10(np.clip(s, 1e-10, 1))       # p-valor caindo = linha subindo
        # verde-petróleo: comprimento (cruza 0,01 às 11:25:45); cinza: confiança do 7 classes (11:24:45)
        pk = np.clip(np.minimum(0.6, 10 ** (-(np.minimum(T, 28) - 25.0) * 2.67)), 1e-10, 1)
        pk2 = np.clip(np.minimum(0.5, 10 ** (-(np.minimum(T, 28) - 24.5) * 8.0)), 1e-10, 1)
        ymax = 10.5
        def py(v):
            return (y1 - 0.30) - lp(v) / ymax * ((y1 - 0.30) - (y0 + 0.08))
        x0, x1 = a + 0.10, X1 - 0.10
        px = lambda t: x0 + (t - T[0]) / (T[-1] - T[0]) * (x1 - x0)
        ax.add_patch(Rectangle((px(FIM_ESTAVEL), y0 + 0.08), px(FIM_PT) - px(FIM_ESTAVEL),
                               (y1 - 0.30) - (y0 + 0.08), fc=FAIXA, ec="none"))
        ax.plot([x0, x1], [py(0.01)] * 2, color=VERM, lw=0.8, ls=(0, (3, 2)))
        ax.plot(px(T), py(pk2), color=CINZA, lw=0.8)
        ax.plot(px(T), py(pk), color=PET, lw=1.6)
        ax.plot([x0, x0], [y0 + 0.08, y1 - 0.30], color=CINZA, lw=0.7)
    elif i == 2:    # distribuições
        gaps = 0.08; w = (wtot - gaps) / 2
        painel(ax, X0, y0, X0 + w, y1, "comprimento por faixa")
        ref = [0.7, 2, 10, 45, 41, 1.3, 0, 0]
        pt = [24, 4, 16, 11, 21, 6, 12, 6]
        mini_barras(ax, X0 + 0.10, y0 + 0.07, X0 + w - 0.10, y1 - 0.30, ref, pt, 48)
        a = X0 + w + gaps
        painel(ax, a, y0, X1, y1, "classes previstas")
        ref = [45, 17, 12, 10, 8, 5, 3]
        at = [97, 0, 3, 0, 0, 0, 0]
        mini_barras(ax, a + 0.10, y0 + 0.07, X1 - 0.10, y1 - 0.30, ref, at, 100)
    else:           # estados do alerta
        painel(ax, X0, y0, X1, y1, "alerta por instância")
        x0, x1 = X0 + 0.10, X1 - 0.10
        px = lambda t: x0 + (t - T[0]) / (T[-1] - T[0]) * (x1 - x0)
        # mesma ordem e mesmos estados da Figura 11: 3 classes (comprimento, classe, confiança),
        # depois 7 classes (comprimento, classe, confiança); 5 das 6 instâncias disparam
        linhas = [(25.0, 26.0), (26.5, 27.5), (26.5, 27.5), (25.0, 26.0), (25.5, 26.5), (None, None)]
        hb, yb = 0.056, y1 - 0.30
        for k, (p, f) in enumerate(linhas):
            yy = yb - k * (hb + 0.024)
            ax.add_patch(Rectangle((x0, yy), x1 - x0, hb, fc=NORMAL, ec="none"))
            if p:
                ax.add_patch(Rectangle((px(p), yy), px(f) - px(p), hb, fc=LARANJA, ec="none"))
                ax.add_patch(Rectangle((px(f), yy), x1 - px(f), hb, fc=VERM, ec="none"))
        # legenda dos estados (texto, não só cor)
        lx = X0 + 1.62
        for nome, c in (("Normal", NORMAL), ("Pending", LARANJA), ("Firing", VERM)):
            ax.add_patch(Rectangle((lx, y1 - 0.17), 0.13, 0.08, fc=c, ec="none"))
            ax.text(lx + 0.17, y1 - 0.13, nome, ha="left", va="center", fontsize=9, color=TXT)
            lx += 0.17 + len(nome) * 0.075 + 0.14


# =================================================================== Figura 14: anatomia
def chamada(fig_ax, x, y, n):
    fig_ax.add_patch(Circle((x, y), 0.105, fc=TXT, ec="white", lw=1.2, zorder=20))
    fig_ax.text(x, y, str(n), ha="center", va="center", color="white", fontsize=9.5, weight="semibold",
                zorder=21)


def figura14():
    W, H = 6.0, 4.0
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    cam = fig.add_axes([0, 0, 1, 1]); cam.set_xlim(0, W); cam.set_ylim(0, H); cam.axis("off")
    cam.set_zorder(10); cam.patch.set_alpha(0)

    # gráfico
    gx0, gy0, gw, gh = 0.78, 1.18, 3.10, 2.02
    ax = fig.add_axes([gx0 / W, gy0 / H, gw / W, gh / H])
    cam.text(0.42, 3.80, "O comprimento das mensagens mudou às 11:24", fontsize=11.5, weight="semibold",
             color=TXT, va="center")
    cam.text(0.42, 3.55, "PSI de cada variável, calculado a cada 15 s", fontsize=9, color=CINZA_ESC,
             va="center")
    ax.axvspan(FIM_ESTAVEL, FIM_PT, color=FAIXA, lw=0, zorder=0)
    ax.text(21.75, 4.33, "fase estável", ha="center", va="bottom", fontsize=9, color=CINZA_ESC)
    ax.text(26.0, 4.33, "português", ha="center", va="bottom", fontsize=9, color=CINZA_ESC)
    for y in (C7, CL3, CF3, CF7):
        ax.plot(T, y, color=CINZA, lw=1.0, zorder=2)
    ax.axhline(0.25, color=VERM, lw=1.0, ls=(0, (4, 3)), zorder=3)
    rot_limiar = ax.text(T[0] + 0.1, 0.36, "limiar de alerta (0,25)", fontsize=9, color=TXT, va="bottom")
    ax.plot(T, COMP, color=PET, lw=2.4, zorder=5, solid_capstyle="round")
    ax.text(28.25, 2.98, "comprimento", fontsize=9.5, weight="semibold", color=TXT, ha="center", va="bottom")
    ax.text(28.25, 0.42, "outras", fontsize=9, color=CINZA_ESC, ha="center", va="bottom")
    ax.set_xlim(T[0], T[-1]); ax.set_ylim(0, 4.3)
    ax.set_xticks([20, 22, 24, 26, 28]); ax.set_xticklabels([hhmm(m) for m in (20, 22, 24, 26, 28)])
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_ylabel("PSI", fontsize=10, color=TXT, labelpad=4)
    ax.set_xlabel("horário (20/11)", fontsize=9.5, color=TXT, labelpad=3)
    ax.tick_params(labelsize=9.5)
    ax.grid(axis="y", color="#EEEEEE", lw=0.8, zorder=0)
    limpa(ax)

    def d2f(x, y):   # dados -> coordenadas da camada (polegadas)
        X, Y = ax.transData.transform((x, y))
        return cam.transData.inverted().transform((X, Y))

    # legenda da figura simulada (como sai no documento)
    cx0, cy1 = 0.42, 0.58
    cam.plot([cx0, gx0 + gw], [cy1 + 0.07, cy1 + 0.07], color="#E4E4E4", lw=0.8)
    cam.text(cx0, cy1, "Linha verde-petróleo: comprimento. Linhas cinza: outras variáveis.\n"
             "Tracejado: limiar do alerta. Faixa cinza: fase em português.",
             fontproperties=ITALICO, fontsize=10.5, color=TXT, va="top", linespacing=1.15)

    # chamadas: marcador ao lado do elemento, seta curta só quando o elemento é uma linha
    seta_k = dict(cor=TXT, lw=0.9)
    chamada(cam, 0.20, 3.80, 1)                                   # título
    c2 = d2f(24.75, 2.45); chamada(cam, *c2, 2)                    # linha em destaque
    seta(cam, (c2[0] + 0.08, c2[1] - 0.08), d2f(25.45, 1.45), **seta_k)
    chamada(cam, *d2f(27.55, 4.43), 3)                             # rótulo da fase
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    bl = rot_limiar.get_window_extent(rend)
    xr, yc = cam.transData.inverted().transform((bl.x1, (bl.y0 + bl.y1) / 2))
    chamada(cam, xr + 0.13, yc, 3)                                 # rótulo do limiar
    xl = ax.xaxis.label.get_window_extent(rend)
    xr, yc = cam.transData.inverted().transform((xl.x1, (xl.y0 + xl.y1) / 2))
    chamada(cam, xr + 0.20, yc, 4)                                 # rótulos e unidades
    chamada(cam, 0.20, 0.50, 5)                                    # legenda da figura

    # chave das chamadas
    kx, ky = 4.22, 3.18
    cam.text(kx - 0.02, ky + 0.42, "Princípios", fontsize=10, weight="semibold", color=TXT, va="center")
    itens = ["Título que afirma\na conclusão", "Cor só no que\nimporta, cinza\nno resto",
             "Limiar e fases\nrotulados no\npróprio gráfico", "Rótulos e unidades\nem português,\nlegíveis no papel",
             "Legenda da figura\nensina a ler"]
    yy = ky
    for k, t in enumerate(itens, 1):
        chamada(cam, kx + 0.10, yy - 0.05, k)
        cam.text(kx + 0.28, yy + 0.04, t, fontsize=9, color=TXT, va="top", linespacing=1.12)
        yy -= 0.20 + 0.155 * (t.count("\n") + 1)
    fig.savefig(AQUI / "fig14-anatomia.png", dpi=DPI, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    figura12()
    figura13()
    figura14()
    print("ok:", sorted(p.name for p in AQUI.glob("fig1*.png")))
