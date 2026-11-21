#!/usr/bin/env python3
"""
gui.py - Interface Gráfica Desktop com Bordas Suaves e Arredondadas (Anti-Aliasing).
100% nativa em Python (Tkinter + Pillow, sem dependências extras).
Com cantos arredondados nativos do Windows 11 (DWM API), botões suavizados e integração com App Mode.
"""

import ctypes
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw, ImageTk

# Importa o motor de processamento local
from separar_notas import processar_pdf

DIRETORIO_ATUAL = Path(__file__).parent.resolve()
ICONE_ICO = DIRETORIO_ATUAL / "app_icon.ico"
CONFIG_FILE = DIRETORIO_ATUAL / "config.json"

CONFIG_PADRAO = {
    "juntar_boletos": True,
    "salvar_outros": True,
    "limpar_cnpj_nome": True,
    "pasta_saida_padrao": str(Path.home() / "Desktop" / "Notas_Separadas"),
    "formato_nome_nota": "NF {nf} - {nome}",
}


def carregar_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**CONFIG_PADRAO, **cfg}
        except Exception:
            pass
    return CONFIG_PADRAO.copy()


def salvar_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def aplicar_cantos_arredondados_windows(janela):
    """Ativa o arredondamento suave nativo de cantos do Windows 11 (DWM API)."""
    try:
        janela.update()
        hwnd = ctypes.windll.user32.GetParent(janela.winfo_id())
        if not hwnd:
            hwnd = janela.winfo_id()
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        preference = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(preference),
            ctypes.sizeof(preference)
        )
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Componente de Botão Suavizado com Cantos Arredondados (Pillow Anti-Aliasing)
# ----------------------------------------------------------------------------

class BotaoArredondado(tk.Label):
    """Botão ultra-suave com cantos arredondados e anti-aliasing via Pillow."""
    def __init__(
        self, parent, text, command=None, width=140, height=38, radius=10,
        bg_color="#4f46e5", hover_color="#4338ca", fg_color="#ffffff",
        font=("Segoe UI", 9, "bold"), disabled_bg="#94a3b8", disabled_fg="#e2e8f0",
        border_color=None, cursor="hand2", **kwargs
    ):
        parent_bg = parent.cget("bg")
        super().__init__(parent, relief="flat", bd=0, highlightthickness=0, bg=parent_bg, **kwargs)
        self.command = command
        self.width = width
        self.height = height
        self.radius = radius
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.fg_color = fg_color
        self.disabled_bg = disabled_bg
        self.disabled_fg = disabled_fg
        self.border_color = border_color
        self.btn_font = font
        self.is_enabled = True
        self.custom_cursor = cursor
        self.parent_bg = parent_bg

        # Renderiza imagens anti-aliased em 4x supersampling
        self.img_normal = self._render_rounded(self.bg_color, self.border_color)
        self.img_hover = self._render_rounded(self.hover_color, self.border_color)
        self.img_disabled = self._render_rounded(self.disabled_bg, None)

        self.configure(
            image=self.img_normal,
            compound="center",
            text=text,
            fg=self.fg_color,
            font=self.btn_font,
            cursor=self.custom_cursor
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _render_rounded(self, fill_color, border_color):
        scale = 4
        w = int(self.width * scale)
        h = int(self.height * scale)
        r = int(self.radius * scale)
        
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [0, 0, w - 1, h - 1],
            radius=r,
            fill=fill_color,
            outline=border_color,
            width=scale if border_color else 0
        )
        img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    def _on_enter(self, event=None):
        if self.is_enabled:
            self.configure(image=self.img_hover)

    def _on_leave(self, event=None):
        if self.is_enabled:
            self.configure(image=self.img_normal)

    def _on_click(self, event=None):
        if self.is_enabled and self.command:
            self.command()

    def config_state(self, state):
        if state == "disabled":
            self.is_enabled = False
            self.configure(image=self.img_disabled, fg=self.disabled_fg, cursor="arrow")
        else:
            self.is_enabled = True
            self.configure(image=self.img_normal, fg=self.fg_color, cursor=self.custom_cursor)


# ----------------------------------------------------------------------------
# Janela Modal de Configurações Suavizada
# ----------------------------------------------------------------------------

class JanelaConfiguracoes(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configurações do Separador")
        self.geometry("560x490")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        aplicar_cantos_arredondados_windows(self)
        self.cfg = carregar_config()

        self.c_bg = "#f8fafc"
        self.c_card = "#ffffff"
        self.c_header = "#1e1b4b"
        self.c_accent = "#4f46e5"
        self.c_text = "#0f172a"
        self.c_border = "#e2e8f0"

        self.configure(bg=self.c_bg)
        self._construir_ui()

    def _construir_ui(self):
        # Header Suave
        header = tk.Frame(self, bg=self.c_header, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        lbl = tk.Label(header, text="⚙  Preferências e Padrões do Sistema", font=("Segoe UI", 11, "bold"), fg="white", bg=self.c_header)
        lbl.pack(side="left", padx=22, pady=18)

        # Corpo
        body = tk.Frame(self, bg=self.c_bg, padx=22, pady=18)
        body.pack(fill="both", expand=True)

        # Card Opções Suaves
        card_chk = tk.Frame(body, bg=self.c_card, padx=18, pady=14, relief="flat", highlightbackground=self.c_border, highlightthickness=1)
        card_chk.pack(fill="x", pady=(0, 14))

        tk.Label(card_chk, text="Comportamento Padrão na Inicialização", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_card).pack(anchor="w", pady=(0, 8))

        self.var_juntar = tk.BooleanVar(value=self.cfg.get("juntar_boletos", True))
        c1 = tk.Checkbutton(
            card_chk, text="Sempre juntar Nota + Boleto em PDF único por padrão",
            variable=self.var_juntar, font=("Segoe UI", 9), bg=self.c_card, activebackground=self.c_card, relief="flat"
        )
        c1.pack(anchor="w", pady=4)

        self.var_outros = tk.BooleanVar(value=self.cfg.get("salvar_outros", True))
        c2 = tk.Checkbutton(
            card_chk, text="Sempre salvar Mapas e Acertos de Carga por padrão",
            variable=self.var_outros, font=("Segoe UI", 9), bg=self.c_card, activebackground=self.c_card, relief="flat"
        )
        c2.pack(anchor="w", pady=4)

        self.var_limpar_cnpj = tk.BooleanVar(value=self.cfg.get("limpar_cnpj_nome", True))
        c3 = tk.Checkbutton(
            card_chk, text="Sempre limpar CNPJ do início da Razão Social",
            variable=self.var_limpar_cnpj, font=("Segoe UI", 9), bg=self.c_card, activebackground=self.c_card, relief="flat"
        )
        c3.pack(anchor="w", pady=4)

        # Card Pasta Padrão
        card_pasta = tk.Frame(body, bg=self.c_card, padx=18, pady=14, relief="flat", highlightbackground=self.c_border, highlightthickness=1)
        card_pasta.pack(fill="x", pady=(0, 16))

        tk.Label(card_pasta, text="Pasta de Saída Padrão", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_card).pack(anchor="w", pady=(0, 6))

        row_pasta = tk.Frame(card_pasta, bg=self.c_card)
        row_pasta.pack(fill="x")

        self.var_pasta = tk.StringVar(value=self.cfg.get("pasta_saida_padrao", str(Path.home() / "Desktop" / "Notas_Separadas")))
        e_pasta = tk.Entry(row_pasta, textvariable=self.var_pasta, font=("Segoe UI", 9), bg="#f8fafc", relief="flat", highlightbackground=self.c_border, highlightthickness=1)
        e_pasta.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=5)

        btn_procurar = BotaoArredondado(
            row_pasta, text="Procurar...", command=self._procurar_pasta,
            width=100, height=32, radius=8, bg_color="#e2e8f0", hover_color="#cbd5e1", fg_color="#1e293b",
            font=("Segoe UI", 8, "bold")
        )
        btn_procurar.pack(side="left")

        # Rodapé com Botões Suaves
        footer = tk.Frame(body, bg=self.c_bg)
        footer.pack(fill="x", side="bottom")

        btn_salvar = BotaoArredondado(
            footer, text="✔  Salvar Padrões", command=self._salvar,
            width=140, height=38, radius=10, bg_color="#4f46e5", hover_color="#4338ca", fg_color="#ffffff",
            font=("Segoe UI", 9, "bold")
        )
        btn_salvar.pack(side="right", padx=(8, 0))

        btn_cancelar = BotaoArredondado(
            footer, text="Cancelar", command=self.destroy,
            width=100, height=38, radius=10, bg_color="#e2e8f0", hover_color="#cbd5e1", fg_color="#334155",
            font=("Segoe UI", 9)
        )
        btn_cancelar.pack(side="right")

        btn_reset = BotaoArredondado(
            footer, text="Restaurar Padrões", command=self._restaurar_padrao,
            width=130, height=34, radius=8, bg_color="#f1f5f9", hover_color="#e2e8f0", fg_color="#64748b",
            font=("Segoe UI", 8)
        )
        btn_reset.pack(side="left")

    def _procurar_pasta(self):
        p = filedialog.askdirectory(title="Selecione a Pasta de Saída Padrão")
        if p:
            self.var_pasta.set(p)

    def _restaurar_padrao(self):
        self.var_juntar.set(CONFIG_PADRAO["juntar_boletos"])
        self.var_outros.set(CONFIG_PADRAO["salvar_outros"])
        self.var_limpar_cnpj.set(CONFIG_PADRAO["limpar_cnpj_nome"])
        self.var_pasta.set(CONFIG_PADRAO["pasta_saida_padrao"])

    def _salvar(self):
        nova_cfg = {
            "juntar_boletos": self.var_juntar.get(),
            "salvar_outros": self.var_outros.get(),
            "limpar_cnpj_nome": self.var_limpar_cnpj.get(),
            "pasta_saida_padrao": self.var_pasta.get().strip(),
            "formato_nome_nota": self.cfg.get("formato_nome_nota", "NF {nf} - {nome}"),
        }
        salvar_config(nova_cfg)

        self.parent.var_juntar.set(nova_cfg["juntar_boletos"])
        self.parent.var_outros.set(nova_cfg["salvar_outros"])
        self.parent.var_limpar_cnpj.set(nova_cfg["limpar_cnpj_nome"])
        self.parent.var_saida.set(nova_cfg["pasta_saida_padrao"])

        messagebox.showinfo("Sucesso", "Preferências salvas como padrão com sucesso!")
        self.destroy()


# ----------------------------------------------------------------------------
# Janela Principal do Aplicativo (Suavizada e Integrada)
# ----------------------------------------------------------------------------

class AppSeparador(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Separador de Notas & Boletos")
        self.geometry("980x720")
        self.minsize(880, 620)

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        aplicar_cantos_arredondados_windows(self)
        self.cfg = carregar_config()

        # Paleta de Cores Suave
        self.c_bg = "#f8fafc"           # Slate 50
        self.c_card = "#ffffff"         # Branco
        self.c_header = "#1e1b4b"       # Indigo 950
        self.c_accent = "#4f46e5"       # Indigo 600
        self.c_accent_hover = "#4338ca" # Indigo 700
        self.c_success = "#059669"      # Emerald 600
        self.c_success_hover = "#047857"# Emerald 700
        self.c_text = "#0f172a"         # Slate 900
        self.c_text_muted = "#64748b"   # Slate 500
        self.c_border = "#e2e8f0"       # Slate 200 suave
        self.c_input_bg = "#f8fafc"

        self.configure(bg=self.c_bg)

        self._configurar_estilos()
        self._construir_interface()

    def _configurar_estilos(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure(".", background=self.c_bg, font=("Segoe UI", 9))

        # Estilo da Tabela com linhas suaves e cabeçalho arredondado
        self.style.configure(
            "Custom.Treeview",
            background="white",
            foreground=self.c_text,
            fieldbackground="white",
            rowheight=30,
            font=("Segoe UI", 9),
            borderwidth=0
        )
        self.style.configure(
            "Custom.Treeview.Heading",
            background="#f1f5f9",
            foreground="#334155",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=(8, 8)
        )
        self.style.map(
            "Custom.Treeview",
            background=[("selected", "#e0e7ff")],
            foreground=[("selected", "#1e1b4b")]
        )

        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor="#e2e8f0",
            background=self.c_accent,
            thickness=6,
            relief="flat"
        )

    def _construir_interface(self):
        # --------------------------------------------------------------------
        # 1. Header Superior Moderno
        # --------------------------------------------------------------------
        header = tk.Frame(self, bg=self.c_header, height=72)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        header_content = tk.Frame(header, bg=self.c_header)
        header_content.pack(fill="both", expand=True, padx=24)

        lbl_box = tk.Frame(header_content, bg=self.c_header)
        lbl_box.pack(side="left", pady=12)

        lbl_titulo = tk.Label(
            lbl_box, text="📄  Separador de Notas & Boletos",
            font=("Segoe UI", 13, "bold"), fg="white", bg=self.c_header
        )
        lbl_titulo.pack(anchor="w")

        lbl_sub = tk.Label(
            lbl_box, text="Organização inteligente de DANFEs, Boletos e Cargas • 100% Offline",
            font=("Segoe UI", 8), fg="#c7d2fe", bg=self.c_header
        )
        lbl_sub.pack(anchor="w")

        # Botões do Header
        btn_box = tk.Frame(header_content, bg=self.c_header)
        btn_box.pack(side="right", pady=16)

        # Botão para alternar para a versão Standalone Desktop App (com visual igual ao site)
        btn_modo_app = BotaoArredondado(
            btn_box, text="✨ Abrir Interface Web/App", command=self._abrir_modo_app,
            width=180, height=34, radius=10, bg_color="#312e81", hover_color="#4338ca", fg_color="#38bdf8",
            font=("Segoe UI", 8, "bold")
        )
        btn_modo_app.pack(side="left", padx=(0, 10))

        btn_config = BotaoArredondado(
            btn_box, text="⚙  Configurações", command=self._abrir_configuracoes,
            width=130, height=34, radius=10, bg_color="#312e81", hover_color="#4338ca", fg_color="#e0e7ff",
            font=("Segoe UI", 8, "bold")
        )
        btn_config.pack(side="left", padx=(0, 10))

        badge = tk.Label(
            btn_box, text="● Offline",
            font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#312e81",
            padx=10, pady=6, relief="flat"
        )
        badge.pack(side="left")

        # --------------------------------------------------------------------
        # Container Central
        # --------------------------------------------------------------------
        content = tk.Frame(self, bg=self.c_bg)
        content.pack(fill="both", expand=True, padx=24, pady=16)

        # --------------------------------------------------------------------
        # 2. Card de Arquivos
        # --------------------------------------------------------------------
        card_sel = tk.Frame(
            content, bg=self.c_card, relief="flat",
            highlightbackground=self.c_border, highlightthickness=1
        )
        card_sel.pack(fill="x", pady=(0, 12))

        pad_sel = tk.Frame(card_sel, bg=self.c_card, padx=18, pady=14)
        pad_sel.pack(fill="x")

        # Linha Entrada
        row_in = tk.Frame(pad_sel, bg=self.c_card)
        row_in.pack(fill="x", pady=(0, 8))

        tk.Label(row_in, text="Arquivo da Carga:", width=16, anchor="w", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_card).pack(side="left")
        self.var_entrada = tk.StringVar()
        self.entry_entrada = tk.Entry(
            row_in, textvariable=self.var_entrada, font=("Segoe UI", 9),
            bg=self.c_input_bg, fg=self.c_text, relief="flat", highlightbackground=self.c_border, highlightthickness=1
        )
        self.entry_entrada.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=5)

        btn_pdf = BotaoArredondado(
            row_in, text="📂 Selecionar PDF", command=self._selecionar_pdf,
            width=130, height=32, radius=8, bg_color="#e2e8f0", hover_color="#cbd5e1", fg_color="#1e293b",
            font=("Segoe UI", 8, "bold")
        )
        btn_pdf.pack(side="left", padx=3)

        btn_pasta = BotaoArredondado(
            row_in, text="📁 Pasta Inteira", command=self._selecionar_pasta_origem,
            width=115, height=32, radius=8, bg_color="#e2e8f0", hover_color="#cbd5e1", fg_color="#1e293b",
            font=("Segoe UI", 8)
        )
        btn_pasta.pack(side="left", padx=3)

        # Linha Saída
        row_out = tk.Frame(pad_sel, bg=self.c_card)
        row_out.pack(fill="x")

        tk.Label(row_out, text="Salvar Arquivos em:", width=16, anchor="w", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_card).pack(side="left")
        self.var_saida = tk.StringVar(value=self.cfg.get("pasta_saida_padrao", str(Path.home() / "Desktop" / "Notas_Separadas")))
        self.entry_saida = tk.Entry(
            row_out, textvariable=self.var_saida, font=("Segoe UI", 9),
            bg=self.c_input_bg, fg=self.c_text, relief="flat", highlightbackground=self.c_border, highlightthickness=1
        )
        self.entry_saida.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=5)

        btn_dest = BotaoArredondado(
            row_out, text="Alterar Pasta", command=self._selecionar_pasta_saida,
            width=115, height=32, radius=8, bg_color="#e2e8f0", hover_color="#cbd5e1", fg_color="#1e293b",
            font=("Segoe UI", 8)
        )
        btn_dest.pack(side="left", padx=3)

        # --------------------------------------------------------------------
        # 3. Card de Opções
        # --------------------------------------------------------------------
        card_opts = tk.Frame(
            content, bg=self.c_card, relief="flat",
            highlightbackground=self.c_border, highlightthickness=1
        )
        card_opts.pack(fill="x", pady=(0, 12))

        pad_opts = tk.Frame(card_opts, bg=self.c_card, padx=18, pady=12)
        pad_opts.pack(fill="x")

        header_opts = tk.Frame(pad_opts, bg=self.c_card)
        header_opts.pack(fill="x", pady=(0, 6))

        tk.Label(header_opts, text="Opções da Execução:", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_card).pack(side="left")
        tk.Label(header_opts, text="(Padrões configurados)", font=("Segoe UI", 8), fg=self.c_text_muted, bg=self.c_card).pack(side="left", padx=6)

        opts_row = tk.Frame(pad_opts, bg=self.c_card)
        opts_row.pack(fill="x")

        self.var_juntar = tk.BooleanVar(value=self.cfg.get("juntar_boletos", True))
        chk1 = tk.Checkbutton(
            opts_row, text="Juntar Nota + Boleto em PDF único",
            variable=self.var_juntar, font=("Segoe UI", 9), bg=self.c_card, activebackground=self.c_card, relief="flat"
        )
        chk1.pack(side="left", padx=(0, 24))

        self.var_outros = tk.BooleanVar(value=self.cfg.get("salvar_outros", True))
        chk2 = tk.Checkbutton(
            opts_row, text="Salvar Mapas de Entrega e Acertos de Carga",
            variable=self.var_outros, font=("Segoe UI", 9), bg=self.c_card, activebackground=self.c_card, relief="flat"
        )
        chk2.pack(side="left", padx=(0, 24))

        self.var_limpar_cnpj = tk.BooleanVar(value=self.cfg.get("limpar_cnpj_nome", True))
        chk3 = tk.Checkbutton(
            opts_row, text="Limpar CNPJ da Razão Social",
            variable=self.var_limpar_cnpj, font=("Segoe UI", 9), bg=self.c_card, activebackground=self.c_card, relief="flat"
        )
        chk3.pack(side="left")

        # --------------------------------------------------------------------
        # 4. Barra de Ações Suavizada com Botões Arredondados
        # --------------------------------------------------------------------
        actions_bar = tk.Frame(content, bg=self.c_bg)
        actions_bar.pack(fill="x", pady=(0, 8))

        self.btn_iniciar = BotaoArredondado(
            actions_bar, text="⚡  PROCESSAR E SEPARAR ARQUIVOS", command=self._iniciar_processamento,
            width=250, height=44, radius=12, bg_color=self.c_accent, hover_color=self.c_accent_hover, fg_color="white",
            font=("Segoe UI", 9, "bold")
        )
        self.btn_iniciar.pack(side="left")

        self.btn_abrir_pasta = BotaoArredondado(
            actions_bar, text="📂 Abrir Pasta Gerada", command=self._abrir_pasta_saida,
            width=165, height=44, radius=12, bg_color=self.c_success, hover_color=self.c_success_hover, fg_color="white",
            font=("Segoe UI", 9, "bold")
        )
        self.btn_abrir_pasta.pack(side="left", padx=10)
        self.btn_abrir_pasta.config_state("disabled")

        self.lbl_status = tk.Label(
            actions_bar, text="Pronto para processar.", font=("Segoe UI", 9),
            fg=self.c_text_muted, bg=self.c_bg
        )
        self.lbl_status.pack(side="right", pady=10)

        self.progress_bar = ttk.Progressbar(content, style="Custom.Horizontal.TProgressbar", mode="indeterminate")

        # --------------------------------------------------------------------
        # 5. Tabela de Resultados
        # --------------------------------------------------------------------
        table_card = tk.Frame(
            content, bg=self.c_card, relief="flat",
            highlightbackground=self.c_border, highlightthickness=1
        )
        table_card.pack(fill="both", expand=True)

        colunas = ("tipo", "nf", "nome", "cnpj", "valor", "pgto", "pags")
        self.tree = ttk.Treeview(table_card, columns=colunas, show="headings", style="Custom.Treeview", selectmode="browse")

        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("nf", text="Nº NF")
        self.tree.heading("nome", text="Destinatário / Pagador")
        self.tree.heading("cnpj", text="CNPJ / CPF")
        self.tree.heading("valor", text="Valor Total")
        self.tree.heading("pgto", text="Forma Pgto")
        self.tree.heading("pags", text="Página(s)")

        self.tree.column("tipo", width=90, anchor="center")
        self.tree.column("nf", width=80, anchor="center")
        self.tree.column("nome", width=310, anchor="w")
        self.tree.column("cnpj", width=145, anchor="center")
        self.tree.column("valor", width=110, anchor="e")
        self.tree.column("pgto", width=95, anchor="center")
        self.tree.column("pags", width=75, anchor="center")

        self.tree.tag_configure("par", background="#ffffff")
        self.tree.tag_configure("impar", background="#f8fafc")

        scroll = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ------------------------------------------------------------------------
    # Métodos e Ações
    # ------------------------------------------------------------------------

    def _abrir_configuracoes(self):
        JanelaConfiguracoes(self)

    def _abrir_modo_app(self):
        """Abre instantaneamente o aplicativo em modo Desktop Standalone (idêntico ao site)."""
        bat_launcher = DIRETORIO_ATUAL / "Separador_Notas.bat"
        if bat_launcher.exists():
            subprocess.Popen(["cmd", "/c", str(bat_launcher)], shell=True)

    def _selecionar_pdf(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo PDF da carga",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os Arquivos", "*.*")]
        )
        if caminho:
            self.var_entrada.set(caminho)

    def _selecionar_pasta_origem(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta com vários PDFs")
        if caminho:
            self.var_entrada.set(caminho)

    def _selecionar_pasta_saida(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta de saída")
        if caminho:
            self.var_saida.set(caminho)

    def _abrir_pasta_saida(self):
        pasta = self.var_saida.get().strip()
        if Path(pasta).exists():
            if sys.platform == "win32":
                os.startfile(pasta)
            else:
                subprocess.run(["xdg-open", pasta])

    def _iniciar_processamento(self):
        entrada_str = self.var_entrada.get().strip()
        saida_str = self.var_saida.get().strip()

        if not entrada_str:
            messagebox.showwarning("Atenção", "Por favor, selecione um arquivo PDF ou pasta de entrada primeiro.")
            return

        p_ent = Path(entrada_str)
        if not p_ent.exists():
            messagebox.showerror("Erro", "O arquivo ou pasta selecionada não existe.")
            return

        arquivos = []
        if p_ent.is_dir():
            arquivos = sorted(p_ent.glob("*.pdf"))
        elif p_ent.suffix.lower() == ".pdf":
            arquivos = [p_ent]

        if not arquivos:
            messagebox.showwarning("Atenção", "Nenhum arquivo PDF encontrado no local selecionado.")
            return

        self.btn_iniciar.config_state("disabled")
        self.btn_abrir_pasta.config_state("disabled")
        self.lbl_status.config(text=f"Processando {len(arquivos)} arquivo(s)... Aguarde.")
        self.progress_bar.pack(fill="x", pady=(0, 8), before=self.tree.master)
        self.progress_bar.start(8)

        for item in self.tree.get_children():
            self.tree.delete(item)

        threading.Thread(
            target=self._executar_worker,
            args=(arquivos, Path(saida_str)),
            daemon=True
        ).start()

    def _executar_worker(self, arquivos: list[Path], saida: Path):
        t0 = time.time()
        saida.mkdir(parents=True, exist_ok=True)
        relatorio = []
        totais = {"notas": 0, "boletos": 0, "paginas": 0}

        juntar = self.var_juntar.get()
        salvar_outros = self.var_outros.get()
        limpar_cnpj = self.var_limpar_cnpj.get()

        for pdf in arquivos:
            stats = processar_pdf(
                pdf_path=pdf,
                saida=saida,
                relatorio=relatorio,
                juntar_boletos=juntar,
                salvar_outros=salvar_outros,
                limpar_cnpj_nome=limpar_cnpj
            )
            totais["notas"] += stats["notas"]
            totais["boletos"] += stats["boletos"]
            totais["paginas"] += stats["total_paginas"]

        caminho_csv = saida / "relatorio.csv"
        campos = [
            "origem", "tipo", "nf", "parcela", "nome", "cnpj_cpf",
            "valor_nf", "valor_boleto", "vencimento", "forma_pgto",
            "banco", "paginas", "arquivo", "obs"
        ]
        import csv
        with open(caminho_csv, "w", newline="", encoding="utf-8-sig") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=campos, delimiter=";")
            writer.writeheader()
            writer.writerows(relatorio)

        t_gasto = time.time() - t0
        tempo_str = f"{t_gasto:.1f}s"

        self.after(0, self._finalizar_processamento, totais, relatorio, tempo_str, saida)

    def _finalizar_processamento(self, totais: dict, relatorio: list, tempo_str: str, saida: Path):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_iniciar.config_state("normal")
        self.btn_abrir_pasta.config_state("normal")

        self.lbl_status.config(
            text=f"✅ Concluído em {tempo_str}! {totais['notas']} NFs | {totais['boletos']} Boleto(s)."
        )

        for i, item in enumerate(relatorio):
            tipo_txt = item["tipo"].upper()
            val = item.get("valor_nf") or item.get("valor_boleto") or "-"
            if val != "-":
                val = f"R$ {val}"

            tag = "impar" if i % 2 == 1 else "par"
            self.tree.insert("", "end", values=(
                tipo_txt,
                item.get("nf") or "-",
                item.get("nome") or "-",
                item.get("cnpj_cpf") or "-",
                val,
                item.get("forma_pgto") or "-",
                item.get("paginas") or "-"
            ), tags=(tag,))

        messagebox.showinfo(
            "Processamento Concluído!",
            f"Arquivos separados e organizados com sucesso!\n\n"
            f"⏱ Tempo: {tempo_str}\n"
            f"📄 Notas Fiscais: {totais['notas']}\n"
            f"💳 Boletos: {totais['boletos']}\n"
            f"📑 Total de Páginas: {totais['paginas']}\n\n"
            f"Pasta de destino:\n{saida}"
        )


if __name__ == "__main__":
    app = AppSeparador()
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        app.var_entrada.set(str(Path(sys.argv[1]).resolve()))
    app.mainloop()
