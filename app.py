#!/usr/bin/env python3
"""
app.py - Interface Desktop & Web Self-Hosted para o Separador de Notas Fiscais e Boletos.
Funciona 100% offline com a biblioteca padrão do Python.
Design moderno com bordas ultra-suavizadas (rounded-3xl, sombras suaves e estética elegante).
"""

import argparse
import email
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn

# Importa o motor de processamento do script
from separar_notas import processar_pdf

PASTA_BASE = Path(__file__).parent.resolve()
CONFIG_FILE = PASTA_BASE / "config.json"
TEMP_DOWNLOADS = {}

CONFIG_PADRAO = {
    "juntar_boletos": True,
    "salvar_outros": True,
    "limpar_cnpj_nome": True,
    "pasta_saida_padrao": str(Path.home() / "Desktop" / "Notas_Separadas"),
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


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


HTML_INTERFACE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Separador de Notas & Boletos</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .dragover { border-color: #6366f1 !important; background-color: #f5f3ff !important; transform: scale(1.008); }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f8fafc; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 9999px; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
    </style>
</head>
<body class="bg-slate-50/70 text-slate-800 font-sans min-h-screen flex flex-col antialiased selection:bg-indigo-500 selection:text-white">
    <!-- Navbar Suave -->
    <header class="bg-gradient-to-r from-indigo-950 via-slate-900 to-indigo-950 text-white shadow-sm border-b border-indigo-900/40 sticky top-0 z-40 backdrop-blur">
        <div class="max-w-5xl mx-auto px-6 py-3.5 flex items-center justify-between">
            <div class="flex items-center space-x-3.5">
                <div class="w-10 h-10 rounded-2xl bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center text-emerald-400 text-xl shadow-inner">
                    <i class="fa-solid fa-file-invoice-dollar"></i>
                </div>
                <div>
                    <h1 class="text-base font-bold tracking-tight">Separador de Notas & Boletos</h1>
                    <p class="text-xs text-indigo-200/80">Classificação e organização inteligente • 100% Offline</p>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <button id="btnAbrirConfig" class="flex items-center space-x-1.5 text-xs bg-indigo-900/80 hover:bg-indigo-800 text-indigo-100 px-3.5 py-2 rounded-2xl border border-indigo-700/60 transition-all duration-150 shadow-sm cursor-pointer">
                    <i class="fa-solid fa-gear"></i>
                    <span>Configurações</span>
                </button>
                <div class="flex items-center space-x-2 text-xs bg-indigo-950/80 px-3 py-1.5 rounded-full border border-indigo-800/60">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span class="text-indigo-200 font-medium">Offline</span>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-5xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        <!-- Card de Upload com Bordas Suaves (rounded-3xl) -->
        <div class="bg-white rounded-3xl shadow-sm shadow-slate-200/50 border border-slate-100 p-8 sm:p-10 transition-all">
            <div class="flex items-center justify-between mb-2">
                <h2 class="text-base font-bold text-slate-800 flex items-center gap-2.5">
                    <span class="w-8 h-8 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center text-xs shadow-sm">
                        <i class="fa-solid fa-cloud-arrow-up"></i>
                    </span>
                    Carregar Arquivo PDF da Carga
                </h2>
                <span class="text-[11px] text-slate-400 font-medium bg-slate-50 px-2.5 py-1 rounded-full border border-slate-100">
                    Extração vetorial sem perda
                </span>
            </div>
            <p class="text-xs text-slate-500 mb-6">
                Arraste o arquivo PDF contendo as notas fiscais, boletos e mapas ou clique na área para selecionar.
            </p>

            <form id="uploadForm" enctype="multipart/form-data">
                <!-- Dropzone com cantos arredondados e hover suave -->
                <div id="dropzone" class="border-2 border-dashed border-indigo-200/80 hover:border-indigo-500 rounded-3xl p-8 sm:p-10 text-center cursor-pointer transition-all duration-200 bg-gradient-to-b from-slate-50/40 to-indigo-50/15 group">
                    <input type="file" id="fileInput" name="pdf_file" accept=".pdf" class="hidden">
                    <div class="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-500 flex items-center justify-center mx-auto mb-3.5 group-hover:scale-105 transition-transform duration-200 shadow-sm">
                        <i class="fa-solid fa-file-pdf text-2xl"></i>
                    </div>
                    <p id="fileName" class="text-sm font-semibold text-slate-700">
                        Clique para escolher o PDF ou arraste e solte aqui
                    </p>
                    <p class="text-xs text-slate-400 mt-1">Compatível com DANFEs da SEFAZ e Boletos FEBRABAN</p>
                </div>

                <!-- Opções de Configuração com Bordas Suaves -->
                <div class="mt-6 pt-6 border-t border-slate-100">
                    <div class="flex items-center justify-between mb-3">
                        <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider">Opções de Execução:</h3>
                        <span class="text-[11px] text-slate-400 font-normal">Padrões definidos em Configurações</span>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3.5">
                        <label class="flex items-start gap-3 p-4 rounded-2xl border border-slate-100 bg-slate-50/60 hover:bg-slate-50 hover:border-indigo-200 transition-all cursor-pointer">
                            <input type="checkbox" id="optJuntar" name="juntar" class="mt-1 rounded-md text-indigo-600 focus:ring-indigo-500 cursor-pointer">
                            <div>
                                <span class="text-xs font-bold text-slate-800 block">Juntar Nota + Boleto</span>
                                <span class="text-[11px] text-slate-500 block mt-0.5 leading-snug">Cria PDF unificado (DANFE + Boleto) para envio ao cliente.</span>
                            </div>
                        </label>

                        <label class="flex items-start gap-3 p-4 rounded-2xl border border-slate-100 bg-slate-50/60 hover:bg-slate-50 hover:border-indigo-200 transition-all cursor-pointer">
                            <input type="checkbox" id="optSalvarOutros" name="salvar_outros" class="mt-1 rounded-md text-indigo-600 focus:ring-indigo-500 cursor-pointer">
                            <div>
                                <span class="text-xs font-bold text-slate-800 block">Preservar Mapas/Acertos</span>
                                <span class="text-[11px] text-slate-500 block mt-0.5 leading-snug">Salva mapas de entrega e folhas do motorista.</span>
                            </div>
                        </label>

                        <label class="flex items-start gap-3 p-4 rounded-2xl border border-slate-100 bg-slate-50/60 hover:bg-slate-50 hover:border-indigo-200 transition-all cursor-pointer">
                            <input type="checkbox" id="optLimparCnpj" name="limpar_cnpj" class="mt-1 rounded-md text-indigo-600 focus:ring-indigo-500 cursor-pointer">
                            <div>
                                <span class="text-xs font-bold text-slate-800 block">Limpar CNPJ da Razão</span>
                                <span class="text-[11px] text-slate-500 block mt-0.5 leading-snug">Remove CNPJs no início do nome da empresa.</span>
                            </div>
                        </label>
                    </div>
                </div>

                <!-- Botão de Ação -->
                <div class="mt-7 flex justify-end">
                    <button type="button" id="btnProcessar" class="bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-semibold px-7 py-3 rounded-2xl shadow-sm shadow-indigo-200 flex items-center gap-2 text-xs transition-all duration-150 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
                        <i class="fa-solid fa-bolt"></i>
                        <span>Processar e Separar Arquivos</span>
                    </button>
                </div>
            </form>
        </div>

        <!-- Indicador de Carregamento -->
        <div id="loadingIndicator" class="hidden bg-white rounded-3xl shadow-sm border border-slate-100 p-8 text-center">
            <div class="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-3">
                <i class="fa-solid fa-circle-notch fa-spin text-xl"></i>
            </div>
            <p class="text-sm font-bold text-slate-800">Processando e classificando páginas do PDF...</p>
            <p class="text-xs text-slate-400 mt-1">Extraindo chaves de acesso de 44 dígitos e boletos com precisão.</p>
        </div>

        <!-- Resultados -->
        <div id="resultsCard" class="hidden space-y-6">
            <!-- Métricas Principais em Cards Arredondados -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div class="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm text-center">
                    <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Notas Fiscais</p>
                    <p id="statNotas" class="text-3xl font-extrabold text-indigo-600 mt-1">0</p>
                </div>
                <div class="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm text-center">
                    <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Boletos</p>
                    <p id="statBoletos" class="text-3xl font-extrabold text-emerald-600 mt-1">0</p>
                </div>
                <div class="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm text-center">
                    <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Mapas / Acertos</p>
                    <p id="statOutros" class="text-3xl font-extrabold text-blue-600 mt-1">0</p>
                </div>
                <div class="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm text-center">
                    <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Tempo Gasto</p>
                    <p id="statTempo" class="text-3xl font-extrabold text-slate-700 mt-1">0s</p>
                </div>
            </div>

            <!-- Banner com Botões de Ação Suaves -->
            <div class="bg-gradient-to-r from-emerald-600 to-teal-700 rounded-3xl p-6 text-white flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm shadow-emerald-200/50">
                <div>
                    <h3 class="font-bold text-base flex items-center gap-2">
                        <i class="fa-solid fa-circle-check text-emerald-300"></i>
                        Arquivos organizados e salvos com sucesso!
                    </h3>
                    <p id="txtDestino" class="text-xs text-emerald-100/90 mt-0.5">Os arquivos foram salvos na sua pasta e também estão prontos para download.</p>
                </div>
                <div class="flex items-center gap-3">
                    <button id="btnAbrirPasta" class="bg-emerald-800/80 hover:bg-emerald-900 text-white font-bold px-4 py-2.5 rounded-2xl border border-emerald-500/40 shadow-sm text-xs flex items-center gap-2 whitespace-nowrap transition-all duration-150 cursor-pointer">
                        <i class="fa-solid fa-folder-open text-emerald-300"></i>
                        <span>Abrir Pasta</span>
                    </button>
                    <a id="btnDownloadZip" href="#" class="bg-white text-emerald-800 hover:bg-emerald-50 font-bold px-5 py-2.5 rounded-2xl shadow-sm text-xs flex items-center gap-2 whitespace-nowrap transition-all duration-150">
                        <i class="fa-solid fa-file-zipper text-emerald-600"></i>
                        <span>Baixar .ZIP</span>
                    </a>
                </div>
            </div>

            <!-- Tabela de Itens com Cantos Arredondados -->
            <div class="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
                <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                    <h3 class="font-bold text-slate-800 text-xs uppercase tracking-wider">Documentos Identificados</h3>
                    <span id="badgeCarga" class="text-xs bg-slate-100 text-slate-600 px-3 py-1 rounded-full font-semibold"></span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-100">
                            <tr>
                                <th class="px-5 py-3">Tipo</th>
                                <th class="px-5 py-3">NF</th>
                                <th class="px-5 py-3">Cliente / Pagador</th>
                                <th class="px-5 py-3">CNPJ / CPF</th>
                                <th class="px-5 py-3">Valor</th>
                                <th class="px-5 py-3">Forma Pagto</th>
                                <th class="px-5 py-3">Pág(s)</th>
                            </tr>
                        </thead>
                        <tbody id="tabelaCorpo" class="divide-y divide-slate-100 text-slate-700">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>

    <!-- Modal de Configurações Suave -->
    <div id="modalConfig" class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
        <div class="bg-white rounded-3xl shadow-2xl border border-slate-100 w-full max-w-md p-6 sm:p-7 animate-in fade-in zoom-in-95">
            <div class="flex items-center justify-between pb-4 border-b border-slate-100 mb-5">
                <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
                    <span class="w-7 h-7 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center text-xs shadow-sm">
                        <i class="fa-solid fa-gear"></i>
                    </span>
                    Preferências Padrão do Sistema
                </h3>
                <button id="btnFecharConfig" class="text-slate-400 hover:text-slate-600 cursor-pointer">
                    <i class="fa-solid fa-xmark text-lg"></i>
                </button>
            </div>

            <div class="space-y-3">
                <p class="text-xs text-slate-500 mb-2">Defina quais opções devem iniciar marcadas por padrão:</p>
                
                <label class="flex items-center gap-3 p-3.5 rounded-2xl border border-slate-100 bg-slate-50/60 hover:bg-slate-100/60 transition-all cursor-pointer">
                    <input type="checkbox" id="cfgJuntar" class="rounded-md text-indigo-600 focus:ring-indigo-500 cursor-pointer">
                    <span class="text-xs font-semibold text-slate-700">Sempre unificar NF e Boleto por padrão</span>
                </label>

                <label class="flex items-center gap-3 p-3.5 rounded-2xl border border-slate-100 bg-slate-50/60 hover:bg-slate-100/60 transition-all cursor-pointer">
                    <input type="checkbox" id="cfgSalvarOutros" class="rounded-md text-indigo-600 focus:ring-indigo-500 cursor-pointer">
                    <span class="text-xs font-semibold text-slate-700">Sempre salvar Mapas e Acertos de Carga</span>
                </label>

                <label class="flex items-center gap-3 p-3.5 rounded-2xl border border-slate-100 bg-slate-50/60 hover:bg-slate-100/60 transition-all cursor-pointer">
                    <input type="checkbox" id="cfgLimparCnpj" class="rounded-md text-indigo-600 focus:ring-indigo-500 cursor-pointer">
                    <span class="text-xs font-semibold text-slate-700">Sempre limpar CNPJ da Razão Social</span>
                </label>

                <div class="pt-2">
                    <label class="block text-xs font-semibold text-slate-700 mb-1.5">Pasta de Saída no Computador:</label>
                    <input type="text" id="cfgPastaSaida" class="w-full text-xs font-mono p-3 rounded-2xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-indigo-500 transition-colors">
                </div>
            </div>

            <div class="mt-6 pt-4 border-t border-slate-100 flex items-center justify-end gap-2.5">
                <button id="btnCancelarConfig" class="text-xs text-slate-600 hover:bg-slate-100 px-4 py-2.5 rounded-xl font-medium cursor-pointer transition-colors">Cancelar</button>
                <button id="btnSalvarConfig" class="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-2xl font-semibold shadow-sm flex items-center gap-1.5 cursor-pointer transition-colors">
                    <i class="fa-solid fa-check"></i>
                    <span>Salvar Padrões</span>
                </button>
            </div>
        </div>
    </div>

    <!-- Footer Suave -->
    <footer class="bg-white border-t border-slate-100 py-4 text-center text-xs text-slate-400">
        Separador de Notas & Boletos • Open-Source & Self-Hosted • Antigravity Agent
    </footer>

    <!-- Scripts da Interface -->
    <script>
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const fileName = document.getElementById('fileName');
        const btnProcessar = document.getElementById('btnProcessar');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const resultsCard = document.getElementById('resultsCard');
        const btnAbrirPasta = document.getElementById('btnAbrirPasta');

        const modalConfig = document.getElementById('modalConfig');
        const btnAbrirConfig = document.getElementById('btnAbrirConfig');
        const btnFecharConfig = document.getElementById('btnFecharConfig');
        const btnCancelarConfig = document.getElementById('btnCancelarConfig');
        const btnSalvarConfig = document.getElementById('btnSalvarConfig');

        let ultimaPastaSalva = '';

        async function carregarConfiguracoes() {
            try {
                const resp = await fetch('/api/config');
                if (resp.ok) {
                    const cfg = await resp.json();
                    document.getElementById('optJuntar').checked = cfg.juntar_boletos;
                    document.getElementById('optSalvarOutros').checked = cfg.salvar_outros;
                    document.getElementById('optLimparCnpj').checked = cfg.limpar_cnpj_nome;

                    document.getElementById('cfgJuntar').checked = cfg.juntar_boletos;
                    document.getElementById('cfgSalvarOutros').checked = cfg.salvar_outros;
                    document.getElementById('cfgLimparCnpj').checked = cfg.limpar_cnpj_nome;
                    document.getElementById('cfgPastaSaida').value = cfg.pasta_saida_padrao || '';
                }
            } catch (e) {
                console.error('Erro ao carregar configurações:', e);
            }
        }
        carregarConfiguracoes();

        btnAbrirConfig.addEventListener('click', () => modalConfig.classList.remove('hidden'));
        btnFecharConfig.addEventListener('click', () => modalConfig.classList.add('hidden'));
        btnCancelarConfig.addEventListener('click', () => modalConfig.classList.add('hidden'));

        btnSalvarConfig.addEventListener('click', async () => {
            const novaCfg = {
                juntar_boletos: document.getElementById('cfgJuntar').checked,
                salvar_outros: document.getElementById('cfgSalvarOutros').checked,
                limpar_cnpj_nome: document.getElementById('cfgLimparCnpj').checked,
                pasta_saida_padrao: document.getElementById('cfgPastaSaida').value.trim()
            };

            try {
                const resp = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(novaCfg)
                });
                if (resp.ok) {
                    document.getElementById('optJuntar').checked = novaCfg.juntar_boletos;
                    document.getElementById('optSalvarOutros').checked = novaCfg.salvar_outros;
                    document.getElementById('optLimparCnpj').checked = novaCfg.limpar_cnpj_nome;
                    modalConfig.classList.add('hidden');
                    alert('Padrões salvos com sucesso!');
                }
            } catch (e) {
                alert('Erro ao salvar configurações.');
            }
        });

        btnAbrirPasta.addEventListener('click', async () => {
            try {
                await fetch('/api/abrir-pasta', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pasta: ultimaPastaSalva })
                });
            } catch (e) {
                alert('Erro ao abrir pasta.');
            }
        });

        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                atualizarNomeArquivo();
            }
        });
        fileInput.addEventListener('change', atualizarNomeArquivo);

        function atualizarNomeArquivo() {
            if (fileInput.files.length > 0) {
                fileName.innerHTML = `<span class="text-indigo-600 font-bold">${fileInput.files[0].name}</span> (${(fileInput.files[0].size/1024/1024).toFixed(2)} MB)`;
            }
        }

        btnProcessar.addEventListener('click', async () => {
            if (!fileInput.files.length) {
                alert('Por favor, selecione um arquivo PDF primeiro.');
                return;
            }

            const formData = new FormData();
            formData.append('pdf_file', fileInput.files[0]);
            formData.append('juntar', document.getElementById('optJuntar').checked ? 'true' : 'false');
            formData.append('salvar_outros', document.getElementById('optSalvarOutros').checked ? 'true' : 'false');
            formData.append('limpar_cnpj', document.getElementById('optLimparCnpj').checked ? 'true' : 'false');

            btnProcessar.disabled = true;
            loadingIndicator.classList.remove('hidden');
            resultsCard.classList.add('hidden');

            try {
                const resp = await fetch('/api/processar', {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || 'Erro no processamento');

                document.getElementById('statNotas').innerText = data.stats.notas;
                document.getElementById('statBoletos').innerText = data.stats.boletos;
                document.getElementById('statOutros').innerText = data.stats.mapas + data.stats.acertos;
                document.getElementById('statTempo').innerText = data.stats.tempo_fmt;
                document.getElementById('badgeCarga').innerText = data.stats.carga ? `Carga: ${data.stats.carga}` : 'Sem número de carga';
                document.getElementById('btnDownloadZip').href = `/api/download?id=${data.download_id}`;
                
                if (data.pasta_salva) {
                    ultimaPastaSalva = data.pasta_salva;
                    document.getElementById('txtDestino').innerText = `Arquivos gravados em: ${data.pasta_salva}`;
                }

                const tbody = document.getElementById('tabelaCorpo');
                tbody.innerHTML = '';
                data.relatorio.forEach(item => {
                    let tipoBadge = '';
                    if (item.tipo === 'nota') tipoBadge = '<span class="bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full font-bold">DANFE</span>';
                    else if (item.tipo === 'boleto') tipoBadge = '<span class="bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full font-bold">BOLETO</span>';
                    else if (item.tipo === 'mapa') tipoBadge = '<span class="bg-blue-50 text-blue-700 px-3 py-1 rounded-full font-bold">MAPA</span>';
                    else if (item.tipo === 'acerto') tipoBadge = '<span class="bg-amber-50 text-amber-700 px-3 py-1 rounded-full font-bold">ACERTO</span>';
                    else tipoBadge = `<span class="bg-slate-50 text-slate-700 px-3 py-1 rounded-full">${item.tipo}</span>`;

                    const val = item.valor_nf || item.valor_boleto || '-';
                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-slate-50/70 transition-colors';
                    tr.innerHTML = `
                        <td class="px-5 py-3.5">${tipoBadge}</td>
                        <td class="px-5 py-3.5 font-bold text-slate-800">${item.nf}</td>
                        <td class="px-5 py-3.5 font-medium">${item.nome}</td>
                        <td class="px-5 py-3.5 text-slate-400 font-mono text-[11px]">${item.cnpj_cpf || '-'}</td>
                        <td class="px-5 py-3.5 font-bold text-slate-800">${val ? 'R$ ' + val : '-'}</td>
                        <td class="px-5 py-3.5 text-slate-600">${item.forma_pgto || '-'}</td>
                        <td class="px-5 py-3.5 text-slate-400 font-medium">${item.paginas}</td>
                    `;
                    tbody.appendChild(tr);
                });

                resultsCard.classList.remove('hidden');
            } catch (err) {
                alert('Erro ao processar: ' + err.message);
            } finally {
                btnProcessar.disabled = false;
                loadingIndicator.classList.add('hidden');
            }
        });
    </script>
</body>
</html>
"""


class SeparadorHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            html_bytes = HTML_INTERFACE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)
            self.wfile.flush()
            return

        elif parsed.path == "/api/config":
            cfg = carregar_config()
            cfg_bytes = json.dumps(cfg).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cfg_bytes)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(cfg_bytes)
            self.wfile.flush()
            return

        elif parsed.path == "/favicon.ico":
            ico_path = PASTA_BASE / "app_icon.ico"
            if ico_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.send_header("Content-Length", str(ico_path.stat().st_size))
                self.send_header("Connection", "close")
                self.end_headers()
                with open(ico_path, "rb") as f_ico:
                    self.wfile.write(f_ico.read())
                self.wfile.flush()
                return

        elif parsed.path == "/api/download":
            params = urllib.parse.parse_qs(parsed.query)
            token = params.get("id", [None])[0]
            if token and token in TEMP_DOWNLOADS:
                zip_path, filename = TEMP_DOWNLOADS[token]
                if Path(zip_path).exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "application/zip")
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self.send_header("Content-Length", str(Path(zip_path).stat().st_size))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    with open(zip_path, "rb") as f:
                        shutil.copyfileobj(f, self.wfile)
                    self.wfile.flush()
                    return

            self.send_error(404, "Arquivo não encontrado ou expirado.")
            return

        self.send_error(404, "Rota não encontrada")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/config":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                novos_dados = json.loads(body.decode("utf-8"))
                cfg_atual = carregar_config()
                cfg_atual.update(novos_dados)
                salvar_config(cfg_atual)

                resp = json.dumps({"status": "success", "config": cfg_atual}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(resp)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(resp)
                self.wfile.flush()
                return
            except Exception as e:
                self.send_error(400, f"Erro ao salvar configurações: {str(e)}")
                return

        elif parsed.path == "/api/abrir-pasta":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                req_data = json.loads(body.decode("utf-8")) if length > 0 else {}
                cfg = carregar_config()
                pasta = req_data.get("pasta") or cfg.get("pasta_saida_padrao") or str(Path.home() / "Desktop" / "Notas_Separadas")

                p_pasta = Path(pasta)
                p_pasta.mkdir(parents=True, exist_ok=True)
                if sys.platform == "win32":
                    os.startfile(str(p_pasta))
                else:
                    subprocess.run(["xdg-open", str(p_pasta)])

                resp = json.dumps({"status": "success"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(resp)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(resp)
                self.wfile.flush()
                return
            except Exception as e:
                self.send_error(500, f"Erro ao abrir pasta: {str(e)}")
                return

        elif parsed.path == "/api/processar":
            t0 = time.time()
            content_type = self.headers.get("Content-Type", "")
            if not content_type or "multipart/form-data" not in content_type.lower():
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Content-Type deve ser multipart/form-data"}).encode())
                return

            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                content_length = 0

            raw_body = self.rfile.read(content_length)
            header_bytes = f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
            msg = email.message_from_bytes(header_bytes + raw_body)

            params = {}
            file_data = None
            orig_name = "documento.pdf"

            for part in msg.walk():
                cd = part.get("Content-Disposition", "")
                if "form-data" in cd:
                    name = part.get_param("name", header="content-disposition")
                    fname = part.get_filename()
                    if fname:
                        orig_name = fname
                        file_data = part.get_payload(decode=True)
                    elif name:
                        payload = part.get_payload(decode=True)
                        if payload:
                            params[name] = payload.decode("utf-8", errors="ignore").strip()

            if not file_data:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Nenhum arquivo PDF enviado no campo pdf_file"}).encode())
                return

            # Carrega padrões do config se não vierem explícitos
            cfg = carregar_config()
            juntar = params.get("juntar", str(cfg.get("juntar_boletos", True)).lower()) == "true"
            salvar_outros = params.get("salvar_outros", str(cfg.get("salvar_outros", True)).lower()) == "true"
            limpar_cnpj = params.get("limpar_cnpj", str(cfg.get("limpar_cnpj_nome", True)).lower()) == "true"

            temp_dir = tempfile.mkdtemp(prefix="separador_")
            input_pdf = Path(temp_dir) / orig_name
            with open(input_pdf, "wb") as f_out:
                f_out.write(file_data)

            saida_dir = Path(temp_dir) / "saida"
            saida_dir.mkdir(parents=True, exist_ok=True)
            relatorio = []

            stats = processar_pdf(
                pdf_path=input_pdf,
                saida=saida_dir,
                relatorio=relatorio,
                juntar_boletos=juntar,
                salvar_outros=salvar_outros,
                limpar_cnpj_nome=limpar_cnpj,
            )

            caminho_csv = saida_dir / "relatorio.csv"
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

            # Também copia para a pasta padrão local no computador do usuário
            pasta_local_alvo = Path(cfg.get("pasta_saida_padrao") or str(Path.home() / "Desktop" / "Notas_Separadas"))
            try:
                pasta_local_alvo.mkdir(parents=True, exist_ok=True)
                for item in saida_dir.glob("*"):
                    destino_final = pasta_local_alvo / item.name
                    if item.is_dir():
                        if destino_final.exists():
                            shutil.rmtree(destino_final)
                        shutil.copytree(item, destino_final)
                    else:
                        shutil.copy2(item, destino_final)
                caminho_salvo_str = str(pasta_local_alvo.resolve())
            except Exception:
                caminho_salvo_str = ""

            zip_token = f"carga_{int(time.time())}_{stats.get('carga') or 'resultado'}"
            zip_path = Path(temp_dir) / f"{zip_token}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
                for root, dirs, files in os.walk(saida_dir):
                    for file in files:
                        p = Path(root) / file
                        arcname = p.relative_to(saida_dir)
                        zip_f.write(p, arcname)

            TEMP_DOWNLOADS[zip_token] = (str(zip_path), f"{zip_token}.zip")

            t_decorrido = time.time() - t0
            stats["tempo_fmt"] = f"{t_decorrido:.1f}s"

            resp_data = {
                "status": "success",
                "stats": stats,
                "relatorio": relatorio,
                "download_id": zip_token,
                "pasta_salva": caminho_salvo_str,
            }
            resp_bytes = json.dumps(resp_data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(resp_bytes)
            self.wfile.flush()
            return

        self.send_error(404, "Rota não encontrada")


def run_server(port: int = 5000, host: str = "0.0.0.0"):
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, SeparadorHandler)
    print("=" * 65)
    print("🌐 SERVIDOR INICIADO COM SUCESSO!")
    print(f"🔗 Acesse em: http://localhost:{port}")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor finalizado.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interface do Separador de Notas.")
    parser.add_argument("-p", "--porta", type=int, default=5000, help="Porta HTTP (padrão: 5000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host de binding (padrão: 0.0.0.0)")
    args = parser.parse_args()
    run_server(port=args.porta, host=args.host)
