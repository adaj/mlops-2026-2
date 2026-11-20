"""Diagramas da Parte 2: o mapa da detecção e as curvas acumuladas do KS."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch, Rectangle

plt.rcParams.update({"font.family": "Inter", "font.size": 10.5, "axes.titlesize": 11})
PET, CINZA, CINZA_ESC, VERM, TXT = "#0E7C7B", "#BDBDBD", "#6E6E6E", "#C4162A", "#222222"


def seta(ax, a, b, **kw):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, lw=1.4,
                                 color=kw.pop("color", CINZA_ESC), shrinkA=2, shrinkB=2, **kw))


# ---------------------------------------------------------------- mapa da detecção
fig, ax = plt.subplots(figsize=(6.4, 3.9), dpi=250)
ax.set_xlim(0, 100); ax.set_ylim(0, 61); ax.set_aspect("equal"); ax.axis("off")

# Referência (canto superior esquerdo)
ax.add_patch(FancyBboxPatch((2, 37), 27, 21, boxstyle="round,pad=0.4,rounding_size=1.5",
                            fc="#F4F4F4", ec=CINZA_ESC, lw=1))
ax.text(15.5, 55, "Referência", ha="center", va="center", weight="semibold", color=TXT)
ax.text(15.5, 51.2, "fixa, separada do treino", ha="center", va="center", fontsize=8.5, color=CINZA_ESC)
for i, h in enumerate([3, 9, 7, 2.5]):
    ax.add_patch(Rectangle((8 + i * 4.2, 39.5), 3.4, h, fc="#9A9A9A", ec="none"))

# Produção (canto superior direito)
ax.text(78, 58, "Produção", ha="center", va="center", weight="semibold", color=TXT)
xs = [62 + i * 4.4 for i in range(8)]
for x in xs:
    ax.add_patch(Rectangle((x, 44), 3.5, 3.5, fc=PET, ec="none"))
x0, x1 = xs[0], xs[-1] + 3.5
ax.plot([x0, x0, x1, x1], [49, 50.6, 50.6, 49], color=TXT, lw=1)
ax.text((x0 + x1) / 2, 52.0, "janela deslizante: últimas N mensagens", ha="center", va="bottom",
        fontsize=8.3, color=TXT)
seta(ax, (99.8, 45.8), (x1 + 0.6, 45.8), color=PET)
ax.text(99.8, 42.6, "nova mensagem entra", ha="right", va="top", fontsize=8, color=PET)
ax.add_patch(Rectangle((xs[0] - 4.6, 39.5), 3.5, 3.5, fc="#DDDDDD", ec="none"))
seta(ax, (xs[0] + 0.5, 43.6), (xs[0] - 1.3, 42.2), color=CINZA)
ax.text(xs[0] - 6.0, 41.2, "a mais antiga sai", ha="right", va="center", fontsize=8, color=CINZA_ESC)

# Cálculo periódico (centro)
cx, cy = 42, 28
ax.add_patch(Circle((cx, cy), 8.0, fc="white", ec=TXT, lw=1.2))
ax.text(cx, cy + 2.3, "cálculo", ha="center", va="center", fontsize=9.5, weight="semibold", color=TXT)
ax.text(cx, cy - 0.7, "periódico", ha="center", va="center", fontsize=9.5, weight="semibold", color=TXT)
ax.text(cx, cy - 4.3, "PSI · KS", ha="center", va="center", fontsize=8.5, color=CINZA_ESC)
seta(ax, (24, 36.5), (cx - 5.8, cy + 5.6))
seta(ax, (xs[0] + 1.5, 43.4), (cx + 6.0, cy + 5.4))
ax.text(cx, cy - 9.8, "a cada intervalo fixo, se a\njanela já tem o mínimo\nde amostras",
        ha="center", va="top", fontsize=7.8, color=CINZA_ESC, linespacing=1.25)

# Série de drift (canto inferior direito)
sx0, sy0, sw, sh = 60, 6, 37, 22
ax.plot([sx0, sx0 + sw], [sy0, sy0], color=CINZA, lw=1)
ax.plot([sx0, sx0], [sy0, sy0 + sh], color=CINZA, lw=1)
vals = [0.10, 0.08, 0.12, 0.09, 0.11, 0.35, 0.9, 1.6, 2.2, 2.4]
X = [sx0 + 2 + i * (sw - 4) / (len(vals) - 1) for i in range(len(vals))]
Y = [sy0 + 1 + v / 2.6 * (sh - 3) for v in vals]
yl = sy0 + 1 + 0.25 / 2.6 * (sh - 3)
ax.plot([sx0, sx0 + sw], [yl, yl], color=VERM, lw=1, ls=(0, (4, 3)))
ax.text(sx0 + 1, yl + 1.0, "limiar", ha="left", va="bottom", fontsize=7.5, color=VERM)
ax.plot(X, Y, color=PET, lw=1.6)
ax.scatter(X, Y, s=10, color=PET, zorder=3)
ax.text(sx0 + sw / 2, sy0 - 1.6, "medida de drift ao longo do tempo", ha="center", va="top",
        fontsize=8.3, color=TXT)
seta(ax, (cx + 8.0, cy), (X[-1] - 1.2, Y[-1]), connectionstyle="arc3,rad=-0.12")
ax.text(66, 31.5, "cada cálculo = 1 ponto", ha="left", va="bottom", fontsize=8, color=CINZA_ESC)

fig.savefig("fig03-mapa-deteccao.png", bbox_inches="tight", pad_inches=0.08, facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- curvas acumuladas
v = list(range(0, 16))
ref = [0, .15, .33, .50, .58, .65, .71, .78, .85, .89, .92, .95, .97, .98, .99, 1.0]
jan = [0, .05, .13, .25, .34, .43, .51, .58, .65, .71, .77, .83, .88, .92, .96, 1.0]
dist = [abs(a - b) for a, b in zip(ref, jan)]
k = max(range(len(v)), key=lambda i: dist[i])

fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=250)
ax.step(v, ref, where="post", color=CINZA_ESC, lw=2.2, label="referência")
ax.step(v, jan, where="post", color=PET, lw=2.2, label="janela")
ax.scatter([v[k], v[k]], [ref[k], jan[k]], color=[CINZA_ESC, PET], s=28, zorder=4)
ax.annotate("", xy=(v[k], jan[k]), xytext=(v[k], ref[k]),
            arrowprops=dict(arrowstyle="<|-|>", color=TXT, lw=1.4, mutation_scale=11))
ax.text(v[k] + 0.25, (ref[k] + jan[k]) / 2, f"D = {dist[k]:.2f}".replace(".", ","),
        va="center", fontsize=11, weight="semibold", color=TXT,
        bbox=dict(fc="white", ec="none", pad=1.5))
for y, c in ((ref[k], CINZA_ESC), (jan[k], PET)):
    ax.plot([0, v[k]], [y, y], color=c, lw=0.8, ls=":")
ax.set_xlim(0, 15.3); ax.set_ylim(0, 1.04)
ax.set_xticks(range(0, 16, 1))
ax.set_yticks([0, .25, .5, .75, 1])
ax.set_yticklabels(["0", "0,25", "0,5", "0,75", "1"])
ax.set_xlabel("comprimento (palavras)", color=TXT)
ax.set_ylabel("fração com até v palavras", color=TXT)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(CINZA)
ax.tick_params(colors=CINZA_ESC)
ax.grid(axis="y", color="#EEEEEE", lw=0.8)
ax.legend(loc="lower right", frameon=False)
fig.savefig("fig04-curvas-ks.png", bbox_inches="tight", pad_inches=0.08, facecolor="white")
print("ok", k, dist[k])
