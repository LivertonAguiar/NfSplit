#!/usr/bin/env python3
"""
gui_moderno.py - NfSplit v1.0.0
Aplicativo Desktop Nativo, 100% Local, Sem Servidor HTTP.
Interface desenvolvida com CustomTkinter, caixas de diálogo integradas,
gestão de pastas persistente, suporte a Arraste e Solte (Drag & Drop) e OTA.
"""

import csv
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog, ttk
from PIL import Image

# Suporte a Arraste e Solte (Drag & Drop) nativo do Windows
try:
    import windnd
    TEM_WINDND = True
except Exception:
    TEM_WINDND = False

# Importações do projeto
from separar_notas import processar_pdf
from updater import AtualizadorOTA, VERSAO_ATUAL

# Configurações de diretório para execução direta e PyInstaller
if getattr(sys, "frozen", False):
    PASTA_BASE = Path(sys.executable).parent.resolve()
    PASTA_INTERNA = Path(sys._MEIPASS).resolve()
else:
    PASTA_BASE = Path(__file__).parent.resolve()
    PASTA_INTERNA = PASTA_BASE

CONFIG_DIR = Path.home() / ".separador_notas"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"

CONFIG_FILE_LOCAL = PASTA_BASE / "config.json"
if CONFIG_FILE_LOCAL.exists():
    CONFIG_FILE = CONFIG_FILE_LOCAL

ICONE_ICO = PASTA_INTERNA / "app_icon.ico"
if not ICONE_ICO.exists():
    ICONE_ICO = PASTA_BASE / "app_icon.ico"

# Configuração Padrão inicial
CONFIG_PADRAO = {
    "juntar_boletos": True,
    "salvar_outros": True,
    "limpar_cnpj_nome": True,
    "pasta_saida_padrao": "",
    "formato_nome_nota": "NF {nf} - {nome}",
    "url_servidor_atualizacao": "",
    "verificar_atualizacoes_auto": False,
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
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


# ----------------------------------------------------------------------------
# Caixas de Diálogo e Modais Nativas do Sistema (Sem usar caixas do Windows)
# ----------------------------------------------------------------------------

class DialogoModerno(ctk.CTkToplevel):
    """Caixa de diálogo modal customizada com cantos arredondados e estética nativa."""

    def __init__(
        self,
        parent,
        titulo: str,
        mensagem: str,
        tipo: str = "info",
        detalhes: str = "",
        callback_abrir_pasta: Optional[callable] = None
    ):
        super().__init__(parent)
        self.parent = parent
        self.resposta = False
        self.callback_abrir_pasta = callback_abrir_pasta

        self.title(titulo)
        self.geometry("490x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.configure(fg_color="#F8FAFC")

        paletas = {
            "sucesso": {"bg_icon": "#059669", "icon": "✔", "titulo": "#065F46"},
            "aviso": {"bg_icon": "#D97706", "icon": "⚠", "titulo": "#92400E"},
            "erro": {"bg_icon": "#DC2626", "icon": "✖", "titulo": "#991B1B"},
            "info": {"bg_icon": "#4F46E5", "icon": "ℹ", "titulo": "#3730A3"},
            "pergunta": {"bg_icon": "#4F46E5", "icon": "❓", "titulo": "#1E1B4B"},
        }
        self.cores = paletas.get(tipo, paletas["info"])
        self.tipo = tipo
        self.titulo_txt = titulo
        self.mensagem_txt = mensagem
        self.detalhes_txt = detalhes

        self._centralizar()
        self._construir_ui()

    def _centralizar(self):
        try:
            self.update_idletasks()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            w, h = 490, 320
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _construir_ui(self):
        card = ctk.CTkFrame(
            self, fg_color="#FFFFFF", corner_radius=18,
            border_width=1, border_color="#E2E8F0"
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(18, 10))

        icone_lbl = ctk.CTkLabel(
            top, text=self.cores["icon"],
            width=46, height=46, corner_radius=14,
            fg_color=self.cores["bg_icon"], text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        icone_lbl.pack(side="left")

        lbl_tit = ctk.CTkLabel(
            top, text=self.titulo_txt,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#0F172A", anchor="w"
        )
        lbl_tit.pack(side="left", padx=14, fill="x", expand=True)

        lbl_msg = ctk.CTkLabel(
            card, text=self.mensagem_txt,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#334155", justify="left", wraplength=410, anchor="w"
        )
        lbl_msg.pack(fill="x", padx=22, pady=(4, 8))

        if self.detalhes_txt:
            box_det = ctk.CTkFrame(card, fg_color="#F8FAFC", corner_radius=10, border_width=1, border_color="#E2E8F0")
            box_det.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            lbl_det = ctk.CTkLabel(
                box_det, text=self.detalhes_txt,
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color="#475569", justify="left", padx=10, pady=8
            )
            lbl_det.pack(fill="both", expand=True)

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=20, pady=(0, 16))

        if self.tipo == "pergunta":
            btn_sim = ctk.CTkButton(
                footer, text="Confirmar", command=self._confirmar,
                width=110, height=36, corner_radius=10, fg_color="#4F46E5", hover_color="#4338CA",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
            )
            btn_sim.pack(side="right", padx=(8, 0))

            btn_nao = ctk.CTkButton(
                footer, text="Cancelar", command=self._cancelar,
                width=90, height=36, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
                text_color="#334155", font=ctk.CTkFont(family="Segoe UI", size=12)
            )
            btn_nao.pack(side="right")

        elif self.tipo == "sucesso" and self.callback_abrir_pasta:
            btn_fechar = ctk.CTkButton(
                footer, text="Concluído", command=self._confirmar,
                width=100, height=36, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
                text_color="#334155", font=ctk.CTkFont(family="Segoe UI", size=12)
            )
            btn_fechar.pack(side="right")

            btn_abrir = ctk.CTkButton(
                footer, text="📂 Abrir Pasta Gerada", command=self._abrir_pasta,
                width=165, height=36, corner_radius=10, fg_color="#059669", hover_color="#047857",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
            )
            btn_abrir.pack(side="right", padx=(0, 8))
        else:
            btn_ok = ctk.CTkButton(
                footer, text="OK", command=self._confirmar,
                width=100, height=36, corner_radius=10, fg_color="#4F46E5", hover_color="#4338CA",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
            )
            btn_ok.pack(side="right")

    def _confirmar(self):
        self.resposta = True
        self.destroy()

    def _cancelar(self):
        self.resposta = False
        self.destroy()

    def _abrir_pasta(self):
        if self.callback_abrir_pasta:
            self.callback_abrir_pasta()
        self.destroy()


def mostrar_aviso(parent, titulo: str, mensagem: str):
    dlg = DialogoModerno(parent, titulo, mensagem, tipo="aviso")
    parent.wait_window(dlg)


def mostrar_erro(parent, titulo: str, mensagem: str, detalhes: str = ""):
    dlg = DialogoModerno(parent, titulo, mensagem, tipo="erro", detalhes=detalhes)
    parent.wait_window(dlg)


def mostrar_sucesso(parent, titulo: str, mensagem: str, detalhes: str = "", callback_abrir_pasta=None):
    dlg = DialogoModerno(parent, titulo, mensagem, tipo="sucesso", detalhes=detalhes, callback_abrir_pasta=callback_abrir_pasta)
    parent.wait_window(dlg)


def mostrar_confirmacao(parent, titulo: str, mensagem: str) -> bool:
    dlg = DialogoModerno(parent, titulo, mensagem, tipo="pergunta")
    parent.wait_window(dlg)
    return dlg.resposta


# ----------------------------------------------------------------------------
# Diálogo Especial: Solicitação de Pasta de Salvamento na Primeira Execução
# ----------------------------------------------------------------------------

class DialogoPrimeiraPasta(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.pasta_escolhida = ""

        self.title("Definir Local de Salvamento")
        self.geometry("520x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.configure(fg_color="#F8FAFC")
        self._construir_ui()

    def _construir_ui(self):
        card = ctk.CTkFrame(
            self, fg_color="#FFFFFF", corner_radius=18,
            border_width=1, border_color="#E2E8F0"
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(18, 10))

        icone = ctk.CTkLabel(
            top, text="📁", width=46, height=46, corner_radius=14,
            fg_color="#EEF2FF", text_color="#4F46E5",
            font=ctk.CTkFont(family="Segoe UI", size=22)
        )
        icone.pack(side="left")

        lbl_tit = ctk.CTkLabel(
            top, text="Onde deseja salvar os arquivos?",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_tit.pack(side="left", padx=14)

        lbl_desc = ctk.CTkLabel(
            card,
            text="Para manter suas notas e boletos organizados, escolha uma pasta no seu computador onde os PDFs separados serão guardados.\n\nEssa pasta ficará salva automaticamente como padrão para os próximos usos.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#475569", justify="left", wraplength=440
        )
        lbl_desc.pack(fill="x", padx=20, pady=(4, 12))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 16))

        sugestao = str(Path.home() / "Desktop" / "Notas_Separadas")
        self.var_caminho = ctk.StringVar(value=sugestao)

        self.entry = ctk.CTkEntry(
            row, textvariable=self.var_caminho, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Button-1>", lambda e: self._procurar())
        if hasattr(self.entry, "_entry"):
            self.entry._entry.configure(cursor="hand2")
            self.entry._entry.bind("<Button-1>", lambda e: self._procurar())
        if hasattr(self.entry, "_canvas"):
            self.entry._canvas.configure(cursor="hand2")

        btn_proc = ctk.CTkButton(
            row, text="Escolher...", command=self._procurar,
            width=90, height=34, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_proc.pack(side="left")

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=20, pady=(0, 16))

        btn_confirmar = ctk.CTkButton(
            footer, text="✔  Salvar Pasta e Continuar", command=self._confirmar,
            width=190, height=38, corner_radius=10, fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        btn_confirmar.pack(side="right", padx=(8, 0))

        btn_cancelar = ctk.CTkButton(
            footer, text="Cancelar", command=self.destroy,
            width=90, height=38, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
            text_color="#334155", font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        btn_cancelar.pack(side="right")

    def _procurar(self):
        p = filedialog.askdirectory(title="Selecione onde salvar as notas separadas")
        if p:
            self.var_caminho.set(p)

    def _confirmar(self):
        caminho = self.var_caminho.get().strip()
        if not caminho:
            mostrar_aviso(self, "Atenção", "Por favor, selecione uma pasta válida para continuar.")
            return
        self.pasta_escolhida = caminho
        self.destroy()


# ----------------------------------------------------------------------------
# Janela Modal: Sobre, Versões, Changelog e Atualizador OTA
# ----------------------------------------------------------------------------

class JanelaSobre(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Sobre o NfSplit • Versões & Atualizações")
        self.geometry("560x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.configure(fg_color="#F8FAFC")
        self.cfg = carregar_config()
        self._construir_ui()

    def _construir_ui(self):
        header = ctk.CTkFrame(self, fg_color="#1E1B4B", corner_radius=0, height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        top_inner = ctk.CTkFrame(header, fg_color="transparent")
        top_inner.pack(fill="both", expand=True, padx=20)

        lbl_tit = ctk.CTkLabel(
            top_inner, text=f"NfSplit v{VERSAO_ATUAL}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_tit.pack(side="left", pady=12)

        badge = ctk.CTkLabel(
            top_inner, text="Release Oficial",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#312E81", text_color="#38BDF8", corner_radius=10, padx=10, pady=4
        )
        badge.pack(side="left", padx=10, pady=18)

        body = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Card Novidades
        card_nov = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_nov.pack(fill="x", pady=(0, 12), padx=2, ipady=4)

        lbl_nov_tit = ctk.CTkLabel(
            card_nov, text="📋 Novidades da Versão 1.0.0",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_nov_tit.pack(anchor="w", padx=16, pady=(10, 6))

        novidades = (
            "• Suporte completo a Arraste e Solte (Drag & Drop) de arquivos PDF.\n"
            "• Executável nativo único (.exe) autônomo, 100% local e sem servidor.\n"
            "• Caixas de diálogo nativas personalizadas integradas à interface.\n"
            "• Solicitação e gravação persistente da pasta de destino na primeira execução.\n"
            "• Extração de DANFEs por Chave de Acesso (44 dígitos) e agregação multi-página.\n"
            "• Leitor universal de boletos FEBRABAN com valores em centavos e vencimentos.\n"
            "• Geração de relatório de faturamento compatível com Microsoft Excel (CSV UTF-8 BOM)."
        )
        lbl_nov_txt = ctk.CTkLabel(
            card_nov, text=novidades,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#475569", justify="left", wraplength=480
        )
        lbl_nov_txt.pack(anchor="w", padx=16, pady=(0, 10))

        # Card OTA
        card_ota = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_ota.pack(fill="x", pady=(0, 14), padx=2, ipady=6)

        top_ota = ctk.CTkFrame(card_ota, fg_color="transparent")
        top_ota.pack(fill="x", padx=16, pady=(10, 6))

        lbl_ota_t = ctk.CTkLabel(
            top_ota, text="🔄 Atualizações de Software (OTA)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_ota_t.pack(side="left")

        status_txt = "⚪ Inativo (Aguardando servidor)"
        cor_status = "#64748B"
        if self.cfg.get("url_servidor_atualizacao"):
            status_txt = "🟢 Configurado"
            cor_status = "#059669"

        lbl_ota_st = ctk.CTkLabel(
            top_ota, text=status_txt,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=cor_status
        )
        lbl_ota_st.pack(side="right")

        lbl_ota_desc = ctk.CTkLabel(
            card_ota,
            text="O NfSplit possui arquitetura OTA integrada para atualização automática direta. Atualmente está inativo aguardando a configuração do seu servidor de distribuição.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748B", justify="left", wraplength=480
        )
        lbl_ota_desc.pack(anchor="w", padx=16, pady=(0, 10))

        btn_verificar = ctk.CTkButton(
            card_ota, text="🔍  Verificar Atualizações Agora", command=self._verificar_atualizacoes,
            width=210, height=34, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_verificar.pack(anchor="w", padx=16, pady=(0, 10))

        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        btn_fechar = ctk.CTkButton(
            footer, text="Fechar", command=self.destroy,
            width=100, height=36, corner_radius=10, fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        btn_fechar.pack(side="right")

    def _verificar_atualizacoes(self):
        url = self.cfg.get("url_servidor_atualizacao", "").strip()
        atualizador = AtualizadorOTA(versao_atual=VERSAO_ATUAL, url_servidor=url)
        sucesso, msg, dados = atualizador.verificar_atualizacao()

        if not url:
            mostrar_aviso(
                self,
                "Sistema OTA Pronto",
                "O módulo de atualização OTA está integrado e pronto para operar.\n\nPara ativá-lo, defina a URL do seu servidor de atualização no arquivo de configurações ou no menu de opções."
            )
        elif sucesso:
            mostrar_sucesso(self, "Nova Versão", msg)
        else:
            mostrar_aviso(self, "Verificação OTA", msg)


# ----------------------------------------------------------------------------
# Janela Modal de Configurações
# ----------------------------------------------------------------------------

class JanelaConfiguracoes(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configurações do NfSplit")
        self.geometry("560x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.cfg = carregar_config()
        self.configure(fg_color="#F8FAFC")
        self._construir_ui()

    def _construir_ui(self):
        header = ctk.CTkFrame(self, fg_color="#1E1B4B", corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        lbl = ctk.CTkLabel(
            header, text="⚙  Preferências e Padrões do Sistema",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl.pack(side="left", padx=24, pady=18)

        body = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        body.pack(fill="both", expand=True, padx=22, pady=16)

        # Card Opções
        card_opts = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_opts.pack(fill="x", pady=(0, 12), padx=2, ipady=6)

        lbl_sec = ctk.CTkLabel(
            card_opts, text="Comportamento Padrão de Processamento",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_sec.pack(anchor="w", padx=16, pady=(10, 8))

        self.var_juntar = ctk.BooleanVar(value=self.cfg.get("juntar_boletos", True))
        c1 = ctk.CTkCheckBox(
            card_opts, text="Sempre juntar Nota + Boleto em PDF único",
            variable=self.var_juntar, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        c1.pack(anchor="w", padx=16, pady=4)

        self.var_outros = ctk.BooleanVar(value=self.cfg.get("salvar_outros", True))
        c2 = ctk.CTkCheckBox(
            card_opts, text="Sempre salvar Mapas e Acertos de Carga por padrão",
            variable=self.var_outros, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        c2.pack(anchor="w", padx=16, pady=4)

        self.var_limpar_cnpj = ctk.BooleanVar(value=self.cfg.get("limpar_cnpj_nome", True))
        c3 = ctk.CTkCheckBox(
            card_opts, text="Sempre limpar CNPJ do início da Razão Social",
            variable=self.var_limpar_cnpj, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        c3.pack(anchor="w", padx=16, pady=(4, 10))

        # Card Pasta Padrão
        card_pasta = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_pasta.pack(fill="x", pady=(0, 12), padx=2, ipady=6)

        lbl_pasta = ctk.CTkLabel(
            card_pasta, text="Pasta de Saída Padrão (Gravada)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_pasta.pack(anchor="w", padx=16, pady=(10, 6))

        row_pasta = ctk.CTkFrame(card_pasta, fg_color="transparent")
        row_pasta.pack(fill="x", padx=16, pady=(0, 10))

        self.var_pasta = ctk.StringVar(value=self.cfg.get("pasta_saida_padrao", ""))
        e_pasta = ctk.CTkEntry(
            row_pasta, textvariable=self.var_pasta, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            placeholder_text="Clique aqui ou em Procurar para definir a pasta...",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        e_pasta.pack(side="left", fill="x", expand=True, padx=(0, 8))
        e_pasta.bind("<Button-1>", lambda e: self._procurar_pasta())
        if hasattr(e_pasta, "_entry"):
            e_pasta._entry.configure(cursor="hand2")
            e_pasta._entry.bind("<Button-1>", lambda e: self._procurar_pasta())
        if hasattr(e_pasta, "_canvas"):
            e_pasta._canvas.configure(cursor="hand2")

        btn_procurar = ctk.CTkButton(
            row_pasta, text="Procurar...", command=self._procurar_pasta,
            width=90, height=34, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#1E293B",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_procurar.pack(side="left")

        # Card Servidor OTA
        card_ota = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_ota.pack(fill="x", pady=(0, 16), padx=2, ipady=6)

        lbl_ota = ctk.CTkLabel(
            card_ota, text="Servidor de Atualizações OTA (Opcional)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_ota.pack(anchor="w", padx=16, pady=(8, 4))

        self.var_ota_url = ctk.StringVar(value=self.cfg.get("url_servidor_atualizacao", ""))
        e_ota = ctk.CTkEntry(
            card_ota, textvariable=self.var_ota_url, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            placeholder_text="https://seuservidor.com/updates/latest.json (deixe vazio se inativo)",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        e_ota.pack(fill="x", padx=16, pady=(0, 10))

        # Rodapé
        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        btn_salvar = ctk.CTkButton(
            footer, text="✔  Salvar Padrões", command=self._salvar,
            width=140, height=38, corner_radius=10, fg_color="#4F46E5",
            hover_color="#4338CA", text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        btn_salvar.pack(side="right", padx=(8, 0))

        btn_cancelar = ctk.CTkButton(
            footer, text="Cancelar", command=self.destroy,
            width=90, height=38, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#334155",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        btn_cancelar.pack(side="right")

        btn_reset = ctk.CTkButton(
            footer, text="Restaurar Padrões", command=self._restaurar_padrao,
            width=130, height=34, corner_radius=8, fg_color="#F1F5F9",
            hover_color="#E2E8F0", text_color="#64748B",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        btn_reset.pack(side="left")

    def _procurar_pasta(self):
        p = filedialog.askdirectory(title="Selecione a Pasta de Saída Padrão")
        if p:
            self.var_pasta.set(p)

    def _restaurar_padrao(self):
        if mostrar_confirmacao(self, "Restaurar Padrões", "Deseja restaurar todas as configurações para o padrão original de fábrica?"):
            self.var_juntar.set(CONFIG_PADRAO["juntar_boletos"])
            self.var_outros.set(CONFIG_PADRAO["salvar_outros"])
            self.var_limpar_cnpj.set(CONFIG_PADRAO["limpar_cnpj_nome"])
            self.var_pasta.set(CONFIG_PADRAO["pasta_saida_padrao"])
            self.var_ota_url.set(CONFIG_PADRAO["url_servidor_atualizacao"])

    def _salvar(self):
        nova_cfg = {
            "juntar_boletos": self.var_juntar.get(),
            "salvar_outros": self.var_outros.get(),
            "limpar_cnpj_nome": self.var_limpar_cnpj.get(),
            "pasta_saida_padrao": self.var_pasta.get().strip(),
            "formato_nome_nota": self.cfg.get("formato_nome_nota", "NF {nf} - {nome}"),
            "url_servidor_atualizacao": self.var_ota_url.get().strip(),
            "verificar_atualizacoes_auto": bool(self.var_ota_url.get().strip()),
        }
        salvar_config(nova_cfg)

        self.parent.var_juntar.set(nova_cfg["juntar_boletos"])
        self.parent.var_outros.set(nova_cfg["salvar_outros"])
        self.parent.var_limpar_cnpj.set(nova_cfg["limpar_cnpj_nome"])
        self.parent.var_saida.set(nova_cfg["pasta_saida_padrao"])

        mostrar_sucesso(self, "Preferências Salvas", "As configurações foram atualizadas e salvas com sucesso!")
        self.destroy()


# ----------------------------------------------------------------------------
# Janela Principal do Aplicativo NfSplit v1.0.0
# ----------------------------------------------------------------------------

class AppSeparador(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NfSplit • Separador de Notas & Boletos")
        self.geometry("1060x780")
        self.minsize(940, 680)

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.cfg = carregar_config()
        self.configure(fg_color="#F8FAFC")

        self._construir_interface()

        # Ativa o suporte a Arraste e Solte (Drag & Drop) nativo
        if TEM_WINDND:
            try:
                windnd.hook_dropfiles(self, func=self._on_arquivos_soltos)
            except Exception:
                pass

    def _construir_interface(self):
        # --------------------------------------------------------------------
        # 1. Header Superior Moderno
        # --------------------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color="#1E1B4B", corner_radius=0, height=72)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=24)

        lbl_box = ctk.CTkFrame(header_content, fg_color="transparent")
        lbl_box.pack(side="left", pady=12)

        lbl_titulo = ctk.CTkLabel(
            lbl_box, text="📄  NfSplit",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_titulo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            lbl_box, text=f"v{VERSAO_ATUAL} • Classificação de DANFEs e Boletos • 100% Offline • Sem Servidor",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#C7D2FE"
        )
        lbl_sub.pack(anchor="w")

        # Botões do Header
        btn_box = ctk.CTkFrame(header_content, fg_color="transparent")
        btn_box.pack(side="right", pady=16)

        btn_sobre = ctk.CTkButton(
            btn_box, text="ℹ  Sobre & OTA", command=self._abrir_sobre,
            width=120, height=36, corner_radius=12, fg_color="#312E81",
            hover_color="#4338CA", text_color="#38BDF8",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_sobre.pack(side="left", padx=(0, 8))

        btn_config = ctk.CTkButton(
            btn_box, text="⚙  Configurações", command=self._abrir_configuracoes,
            width=135, height=36, corner_radius=12, fg_color="#312E81",
            hover_color="#4338CA", text_color="#E0E7FF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_config.pack(side="left", padx=(0, 10))

        badge = ctk.CTkLabel(
            btn_box, text="● 100% Local",
            corner_radius=12, fg_color="#312E81", text_color="#34D399",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=12, pady=6
        )
        badge.pack(side="left")

        # --------------------------------------------------------------------
        # Container Central
        # --------------------------------------------------------------------
        content = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        content.pack(fill="both", expand=True, padx=24, pady=16)

        # --------------------------------------------------------------------
        # 2. Card de Arquivos com Zona de Arraste e Solte (Dropzone)
        # --------------------------------------------------------------------
        card_sel = ctk.CTkFrame(
            content, fg_color="#FFFFFF", corner_radius=16,
            border_width=1, border_color="#E2E8F0"
        )
        card_sel.pack(fill="x", pady=(0, 12), ipady=4)

        pad_sel = ctk.CTkFrame(card_sel, fg_color="transparent")
        pad_sel.pack(fill="x", padx=20, pady=14)

        # Zona Visual de Arraste e Solte (Drag & Drop)
        self.drop_zone = ctk.CTkFrame(
            pad_sel, fg_color="#F8FAFC", corner_radius=12,
            border_width=2, border_color="#C7D2FE", cursor="hand2"
        )
        self.drop_zone.pack(fill="x", pady=(0, 12), ipady=6)
        self.drop_zone.bind("<Button-1>", lambda e: self._selecionar_pdf())

        self.lbl_drop_icon = ctk.CTkLabel(
            self.drop_zone, text="📥",
            font=ctk.CTkFont(size=24), text_color="#4F46E5"
        )
        self.lbl_drop_icon.pack(pady=(6, 2))
        self.lbl_drop_icon.bind("<Button-1>", lambda e: self._selecionar_pdf())

        self.lbl_drop_title = ctk.CTkLabel(
            self.drop_zone, text="Arraste e solte o arquivo PDF da carga aqui",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#1E1B4B"
        )
        self.lbl_drop_title.pack(pady=(0, 2))
        self.lbl_drop_title.bind("<Button-1>", lambda e: self._selecionar_pdf())

        self.lbl_drop_sub = ctk.CTkLabel(
            self.drop_zone, text="ou utilize os botões abaixo para selecionar o arquivo / pasta",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748B"
        )
        self.lbl_drop_sub.pack(pady=(0, 6))
        self.lbl_drop_sub.bind("<Button-1>", lambda e: self._selecionar_pdf())

        # Linha Entrada
        row_in = ctk.CTkFrame(pad_sel, fg_color="transparent")
        row_in.pack(fill="x", pady=(0, 10))

        lbl_ent = ctk.CTkLabel(
            row_in, text="Arquivo da Carga:", width=130, anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_ent.pack(side="left")

        self.var_entrada = ctk.StringVar()
        self.entry_entrada = ctk.CTkEntry(
            row_in, textvariable=self.var_entrada, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            placeholder_text="Clique aqui ou arraste o PDF para carregar...",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.entry_entrada.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_entrada.bind("<Button-1>", lambda e: self._selecionar_pdf())
        if hasattr(self.entry_entrada, "_entry"):
            self.entry_entrada._entry.configure(cursor="hand2")
            self.entry_entrada._entry.bind("<Button-1>", lambda e: self._selecionar_pdf())
        if hasattr(self.entry_entrada, "_canvas"):
            self.entry_entrada._canvas.configure(cursor="hand2")

        btn_pdf = ctk.CTkButton(
            row_in, text="📂 Selecionar PDF", command=self._selecionar_pdf,
            width=135, height=36, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#1E293B",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        btn_pdf.pack(side="left", padx=3)

        btn_pasta = ctk.CTkButton(
            row_in, text="📁 Pasta Inteira", command=self._selecionar_pasta_origem,
            width=115, height=36, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#1E293B",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        btn_pasta.pack(side="left", padx=3)

        # Linha Saída
        row_out = ctk.CTkFrame(pad_sel, fg_color="transparent")
        row_out.pack(fill="x")

        lbl_sai = ctk.CTkLabel(
            row_out, text="Salvar Arquivos em:", width=130, anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_sai.pack(side="left")

        self.var_saida = ctk.StringVar(value=self.cfg.get("pasta_saida_padrao", ""))
        self.entry_saida = ctk.CTkEntry(
            row_out, textvariable=self.var_saida, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            placeholder_text="Clique aqui ou no botão para escolher a pasta...",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.entry_saida.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_saida.bind("<Button-1>", lambda e: self._selecionar_pasta_saida())
        if hasattr(self.entry_saida, "_entry"):
            self.entry_saida._entry.configure(cursor="hand2")
            self.entry_saida._entry.bind("<Button-1>", lambda e: self._selecionar_pasta_saida())
        if hasattr(self.entry_saida, "_canvas"):
            self.entry_saida._canvas.configure(cursor="hand2")

        btn_dest = ctk.CTkButton(
            row_out, text="Alterar Pasta", command=self._selecionar_pasta_saida,
            width=115, height=36, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#1E293B",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        btn_dest.pack(side="left", padx=3)

        # --------------------------------------------------------------------
        # 3. Card de Opções
        # --------------------------------------------------------------------
        card_opts = ctk.CTkFrame(
            content, fg_color="#FFFFFF", corner_radius=16,
            border_width=1, border_color="#E2E8F0"
        )
        card_opts.pack(fill="x", pady=(0, 12), ipady=4)

        pad_opts = ctk.CTkFrame(card_opts, fg_color="transparent")
        pad_opts.pack(fill="x", padx=20, pady=12)

        header_opts = ctk.CTkFrame(pad_opts, fg_color="transparent")
        header_opts.pack(fill="x", pady=(0, 8))

        lbl_opts_t = ctk.CTkLabel(
            header_opts, text="Opções da Execução:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_opts_t.pack(side="left")

        lbl_opts_sub = ctk.CTkLabel(
            header_opts, text="(Padrões configurados)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748B"
        )
        lbl_opts_sub.pack(side="left", padx=6)

        opts_row = ctk.CTkFrame(pad_opts, fg_color="transparent")
        opts_row.pack(fill="x")

        self.var_juntar = ctk.BooleanVar(value=self.cfg.get("juntar_boletos", True))
        chk1 = ctk.CTkCheckBox(
            opts_row, text="Juntar Nota + Boleto em PDF único",
            variable=self.var_juntar, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        chk1.pack(side="left", padx=(0, 24))

        self.var_outros = ctk.BooleanVar(value=self.cfg.get("salvar_outros", True))
        chk2 = ctk.CTkCheckBox(
            opts_row, text="Salvar Mapas de Entrega e Acertos de Carga",
            variable=self.var_outros, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        chk2.pack(side="left", padx=(0, 24))

        self.var_limpar_cnpj = ctk.BooleanVar(value=self.cfg.get("limpar_cnpj_nome", True))
        chk3 = ctk.CTkCheckBox(
            opts_row, text="Limpar CNPJ da Razão Social",
            variable=self.var_limpar_cnpj, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        chk3.pack(side="left")

        # --------------------------------------------------------------------
        # 4. Barra de Ações
        # --------------------------------------------------------------------
        actions_bar = ctk.CTkFrame(content, fg_color="transparent")
        actions_bar.pack(fill="x", pady=(0, 8))

        self.btn_iniciar = ctk.CTkButton(
            actions_bar, text="⚡  PROCESSAR E SEPARAR ARQUIVOS", command=self._iniciar_processamento,
            width=260, height=44, corner_radius=12, fg_color="#4F46E5",
            hover_color="#4338CA", text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.btn_iniciar.pack(side="left")

        self.btn_abrir_pasta = ctk.CTkButton(
            actions_bar, text="📂 Abrir Pasta Gerada", command=self._abrir_pasta_saida,
            width=175, height=44, corner_radius=12, fg_color="#059669",
            hover_color="#047857", text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            state="disabled"
        )
        self.btn_abrir_pasta.pack(side="left", padx=10)

        self.lbl_status = ctk.CTkLabel(
            actions_bar, text="Pronto para processar.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#64748B"
        )
        self.lbl_status.pack(side="right", pady=8)

        self.progress_bar = ctk.CTkProgressBar(
            content, height=8, corner_radius=8,
            fg_color="#E2E8F0", progress_color="#4F46E5", mode="indeterminate"
        )

        # --------------------------------------------------------------------
        # 5. Tabela de Resultados
        # --------------------------------------------------------------------
        table_card = ctk.CTkFrame(
            content, fg_color="#FFFFFF", corner_radius=16,
            border_width=1, border_color="#E2E8F0"
        )
        table_card.pack(fill="both", expand=True)

        table_inner = ttk.Frame(table_card)
        table_inner.pack(fill="both", expand=True, padx=12, pady=12)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Modern.Treeview",
            background="#FFFFFF",
            foreground="#0F172A",
            fieldbackground="#FFFFFF",
            rowheight=30,
            font=("Segoe UI", 9),
            borderwidth=0
        )
        style.configure(
            "Modern.Treeview.Heading",
            background="#F1F5F9",
            foreground="#334155",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=(8, 8)
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", "#E0E7FF")],
            foreground=[("selected", "#1E1B4B")]
        )

        colunas = ("tipo", "nf", "nome", "cnpj", "valor", "pgto", "pags")
        self.tree = ttk.Treeview(
            table_inner, columns=colunas, show="headings",
            style="Modern.Treeview", selectmode="browse"
        )

        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("nf", text="Nº NF")
        self.tree.heading("nome", text="Destinatário / Pagador")
        self.tree.heading("cnpj", text="CNPJ / CPF")
        self.tree.heading("valor", text="Valor Total")
        self.tree.heading("pgto", text="Forma Pgto")
        self.tree.heading("pags", text="Página(s)")

        self.tree.column("tipo", width=90, anchor="center")
        self.tree.column("nf", width=80, anchor="center")
        self.tree.column("nome", width=340, anchor="w")
        self.tree.column("cnpj", width=145, anchor="center")
        self.tree.column("valor", width=110, anchor="e")
        self.tree.column("pgto", width=95, anchor="center")
        self.tree.column("pags", width=75, anchor="center")

        self.tree.tag_configure("par", background="#FFFFFF")
        self.tree.tag_configure("impar", background="#F8FAFC")

        scroll = ttk.Scrollbar(table_inner, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ------------------------------------------------------------------------
    # Métodos e Ações de Arraste e Solte
    # ------------------------------------------------------------------------

    def _on_arquivos_soltos(self, arquivos):
        """Manipula os arquivos arrastados e soltos sobre a janela do aplicativo."""
        if not arquivos:
            return

        caminho = arquivos[0]
        if isinstance(caminho, bytes):
            try:
                caminho = caminho.decode("mbcs")
            except Exception:
                caminho = caminho.decode("utf-8", errors="replace")

        p = Path(caminho)
        if p.is_dir() or p.suffix.lower() == ".pdf":
            self.var_entrada.set(str(p.resolve()))
            self._atualizar_visual_dropzone(p)
            self.lbl_status.configure(text=f"Carregado via Arraste: {p.name}")
        else:
            mostrar_aviso(
                self,
                "Formato Não Suportado",
                f"O arquivo solto ({p.name}) não é um PDF válido.\nPor favor, arraste um arquivo com extensão .pdf ou uma pasta."
            )

    def _atualizar_visual_dropzone(self, p: Path):
        """Atualiza a caixa visual de arraste com informações do arquivo carregado."""
        self.drop_zone.configure(fg_color="#F0FDF4", border_color="#86EFAC")
        self.lbl_drop_icon.configure(text="✔", text_color="#059669")
        self.lbl_drop_title.configure(text=f"Arquivo Carregado: {p.name}", text_color="#065F46")
        self.lbl_drop_sub.configure(
            text="Pronto para processar! Clique em PROCESSAR E SEPARAR ou arraste outro para trocar.",
            text_color="#047857"
        )

    # ------------------------------------------------------------------------
    # Métodos e Ações
    # ------------------------------------------------------------------------

    def _abrir_configuracoes(self):
        JanelaConfiguracoes(self)

    def _abrir_sobre(self):
        JanelaSobre(self)

    def _selecionar_pdf(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo PDF da carga",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os Arquivos", "*.*")]
        )
        if caminho:
            p = Path(caminho)
            self.var_entrada.set(str(p.resolve()))
            self._atualizar_visual_dropzone(p)

    def _selecionar_pasta_origem(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta com vários PDFs")
        if caminho:
            p = Path(caminho)
            self.var_entrada.set(str(p.resolve()))
            self._atualizar_visual_dropzone(p)

    def _selecionar_pasta_saida(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta de saída")
        if caminho:
            self.var_saida.set(caminho)
            self.cfg["pasta_saida_padrao"] = caminho
            salvar_config(self.cfg)

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

        # 1. Validação de Entrada
        if not entrada_str:
            mostrar_aviso(self, "Atenção", "Por favor, arraste ou selecione um arquivo PDF / pasta de entrada primeiro.")
            return

        p_ent = Path(entrada_str)
        if not p_ent.exists():
            mostrar_erro(self, "Arquivo Não Encontrado", "O arquivo ou pasta selecionada não existe mais no computador.")
            return

        # 2. Verificação de Pasta de Destino (Solicita se não configurada)
        if not saida_str:
            dlg_pasta = DialogoPrimeiraPasta(self)
            self.wait_window(dlg_pasta)
            if not dlg_pasta.pasta_escolhida:
                return
            saida_str = dlg_pasta.pasta_escolhida
            self.var_saida.set(saida_str)
            self.cfg["pasta_saida_padrao"] = saida_str
            salvar_config(self.cfg)

        arquivos = []
        if p_ent.is_dir():
            arquivos = sorted(p_ent.glob("*.pdf"))
        elif p_ent.suffix.lower() == ".pdf":
            arquivos = [p_ent]

        if not arquivos:
            mostrar_aviso(self, "Atenção", "Nenhum arquivo PDF encontrado no local selecionado.")
            return

        self.btn_iniciar.configure(state="disabled")
        self.btn_abrir_pasta.configure(state="disabled")
        self.lbl_status.configure(text=f"Processando {len(arquivos)} arquivo(s)... Aguarde.")
        self.progress_bar.pack(fill="x", pady=(0, 8), before=self.tree.master.master)
        self.progress_bar.start()

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
        self.btn_iniciar.configure(state="normal")
        self.btn_abrir_pasta.configure(state="normal")

        self.lbl_status.configure(
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

        resumo_det = (
            f"⏱ Tempo: {tempo_str}\n"
            f"📄 Notas Fiscais: {totais['notas']}\n"
            f"💳 Boletos: {totais['boletos']}\n"
            f"📑 Total de Páginas: {totais['paginas']}\n\n"
            f"Destino: {saida}"
        )
        mostrar_sucesso(
            self,
            "Processamento Concluído!",
            "Os arquivos foram classificados, organizados e salvos com sucesso!",
            detalhes=resumo_det,
            callback_abrir_pasta=self._abrir_pasta_saida
        )


if __name__ == "__main__":
    app = AppSeparador()
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        p = Path(sys.argv[1]).resolve()
        app.var_entrada.set(str(p))
        app._atualizar_visual_dropzone(p)
    app.mainloop()
