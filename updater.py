#!/usr/bin/env python3
"""
updater.py - Módulo de Atualização de Software e Instalação OTA para NfSplit.
Totalmente integrado ao GitHub Releases (LivertonAguiar/NfSplit).
Suporta verificação automática semanal, busca manual, download com progresso
e substituição atômica do executável (.exe) preservando configurações.
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional, Tuple

VERSAO_ATUAL = "1.1.0"
REPOSITORIO_PADRAO = "LivertonAguiar/NfSplit"


def comparar_versoes(v_atual: str, v_nova: str) -> bool:
    """
    Retorna True se v_nova for estritamente mais recente que v_atual.
    Suporta formato semântico X.Y.Z com ou sem prefixo 'v'.
    """
    try:
        def parse(v: str):
            v_limpo = v.strip().lower().lstrip("v")
            partes = []
            for item in v_limpo.split("."):
                num = "".join(ch for ch in item if ch.isdigit())
                if num:
                    partes.append(int(num))
            return partes

        p_nova = parse(v_nova)
        p_atual = parse(v_atual)
        if not p_nova:
            return False
        return p_nova > p_atual
    except Exception:
        return False


def deve_verificar_atualizacao(cfg: dict, dias_intervalo: int = 7) -> bool:
    """
    Retorna True se a checagem automática estiver ativa e se passaram
    pelo menos 'dias_intervalo' dias desde a última verificação.
    """
    if not cfg.get("verificar_atualizacoes_auto", True):
        return False

    ultima_str = cfg.get("ultima_verificacao_atualizacao", "").strip()
    if not ultima_str:
        return True

    try:
        dt_ultima = datetime.fromisoformat(ultima_str)
        return (datetime.now() - dt_ultima) >= timedelta(days=dias_intervalo)
    except Exception:
        return True


class AtualizadorOTA:
    """Gerenciador de verificação, download e aplicação de atualizações OTA via GitHub Releases."""

    def __init__(self, versao_atual: str = VERSAO_ATUAL, repo: str = REPOSITORIO_PADRAO, url_custom: str = ""):
        self.versao_atual = versao_atual
        self.repo = repo.strip() or REPOSITORIO_PADRAO
        if url_custom.strip():
            self.url_api = url_custom.strip()
        else:
            self.url_api = f"https://api.github.com/repos/{self.repo}/releases/latest"

    def verificar_atualizacao(self) -> Tuple[bool, str, Optional[dict]]:
        """
        Consulta o GitHub Releases para verificar se há nova versão disponível.
        Retorna: (tem_nova_versao, mensagem, dados_release)
        """
        try:
            req = urllib.request.Request(
                self.url_api,
                headers={
                    "User-Agent": f"NfSplit-Updater/{self.versao_atual}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    return False, f"Servidor retornou status HTTP {resp.status}.", None
                dados = json.loads(resp.read().decode("utf-8"))

            tag_remota = dados.get("tag_name", "").strip()
            versao_remota = tag_remota.lstrip("v").strip()
            if not versao_remota:
                return False, "Nenhuma versão localizada no GitHub Releases.", None

            # Localiza o executável nos anexos da release
            asset_exe = None
            for asset in dados.get("assets", []):
                nome = asset.get("name", "").lower()
                if nome == "nfsplit.exe" or nome.endswith(".exe"):
                    asset_exe = asset
                    break

            info_versao = {
                "tag": tag_remota,
                "versao": versao_remota,
                "titulo": dados.get("name") or f"NfSplit {tag_remota}",
                "changelog": dados.get("body", "Melhorias gerais e correções no NfSplit."),
                "html_url": dados.get("html_url", ""),
                "publicado_em": dados.get("published_at", ""),
                "tamanho_bytes": asset_exe.get("size", 0) if asset_exe else 0,
                "url_download": asset_exe.get("browser_download_url", "") if asset_exe else "",
                "asset_nome": asset_exe.get("name", "NfSplit.exe") if asset_exe else "",
            }

            if not info_versao["url_download"]:
                return (
                    False,
                    f"A versão {tag_remota} foi encontrada, mas não possui o executável 'NfSplit.exe' anexado.",
                    info_versao
                )

            if comparar_versoes(self.versao_atual, versao_remota):
                return (
                    True,
                    f"Nova versão {tag_remota} disponível para download!",
                    info_versao
                )
            else:
                return (
                    False,
                    f"Você já está utilizando a versão mais recente ({self.versao_atual}).",
                    info_versao
                )

        except urllib.error.URLError as e:
            razao = getattr(e, "reason", str(e))
            return False, f"Não foi possível conectar ao GitHub: {razao}", None
        except json.JSONDecodeError:
            return False, "Resposta inválida retornada pelo GitHub (não é JSON).", None
        except Exception as e:
            return False, f"Erro inesperado ao verificar atualizações: {str(e)}", None

    def baixar_atualizacao(
        self,
        url_download: str,
        callback_progresso: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[bool, str, Optional[Path]]:
        """
        Baixa o arquivo binário da nova versão para um arquivo temporário.
        Chama callback_progresso(bytes_baixados, total_bytes) a cada bloco.
        """
        try:
            fd, temp_path_str = tempfile.mkstemp(prefix="NfSplit_update_", suffix=".exe")
            os.close(fd)
            temp_path = Path(temp_path_str)

            req = urllib.request.Request(
                url_download,
                headers={"User-Agent": f"NfSplit-Updater/{self.versao_atual}"}
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                total_bytes = int(resp.headers.get("Content-Length", 0))
                bytes_baixados = 0
                bloco_tamanho = 128 * 1024  # 128 KB por bloco

                with open(temp_path, "wb") as f_out:
                    while True:
                        bloco = resp.read(bloco_tamanho)
                        if not bloco:
                            break
                        f_out.write(bloco)
                        bytes_baixados += len(bloco)
                        if callback_progresso and total_bytes > 0:
                            callback_progresso(bytes_baixados, total_bytes)

            return True, "Download concluído com sucesso!", temp_path

        except Exception as e:
            return False, f"Erro durante o download da atualização: {str(e)}", None

    @staticmethod
    def aplicar_atualizacao_ota(novo_exe: Path, exe_alvo: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Cria e dispara script em lote (.bat) desanexado que:
        1. Aguarda o término do processo atual (PID);
        2. Substitui o executável atual pelo novo arquivo baixado;
        3. Inicia o novo executável preservando configurações e diretório;
        4. Exclui o script temporário.
        """
        try:
            if exe_alvo is None:
                if getattr(sys, "frozen", False):
                    exe_alvo = Path(sys.executable).resolve()
                else:
                    desktop_exe = Path.home() / "Desktop" / "NfSplit.exe"
                    if desktop_exe.exists():
                        exe_alvo = desktop_exe
                    else:
                        exe_alvo = Path(__file__).parent.resolve() / "NfSplit.exe"

            pid_atual = os.getpid()
            pasta_temp = Path(tempfile.gettempdir())
            bat_script = pasta_temp / f"nfsplit_apply_{pid_atual}.bat"

            script_content = f"""@echo off
chcp 65001 > nul

:loop_espera
tasklist /fi "PID eq {pid_atual}" 2>nul | find "{pid_atual}" >nul
if %errorlevel% equ 0 (
    ping 127.0.0.1 -n 2 > nul
    goto loop_espera
)

rem Substituicao atomica do executavel
move /y "{str(novo_exe)}" "{str(exe_alvo)}" > nul
if %errorlevel% neq 0 (
    copy /y "{str(novo_exe)}" "{str(exe_alvo)}" > nul
    del /f /q "{str(novo_exe)}" > nul
)

rem Reinicia o aplicativo atualizado
start "" "{str(exe_alvo)}"

rem Limpeza do arquivo de script
(goto) 2>nul & del "%~f0"
exit
"""
            with open(bat_script, "w", encoding="utf-8") as f:
                f.write(script_content)

            # Inicia o processo em lote totalmente independente e desanexado
            subprocess.Popen(
                ["cmd.exe", "/c", str(bat_script)],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                close_fds=True
            )
            return True, "Atualização engatilhada com sucesso."

        except Exception as e:
            return False, f"Falha ao agendar instalação da atualização: {str(e)}"
