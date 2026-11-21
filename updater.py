#!/usr/bin/env python3
"""
updater.py - Módulo de Atualização de Software e Instalação OTA (Over-The-Air) para NfSplit.
Preparado para conexão com servidor de atualizações (JSON / GitHub Releases / Servidor próprio).
Por padrão, permanece inativo até que o usuário configure a URL do servidor.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional, Tuple

VERSAO_ATUAL = "1.0.0"


def comparar_versoes(v_atual: str, v_nova: str) -> bool:
    """
    Retorna True se v_nova for estritamente mais recente que v_atual.
    Suporta formato semântico X.Y.Z.
    """
    try:
        def parse(v):
            return [int(x) for x in v.strip().lstrip("v").split(".") if x.isdigit()]
        return parse(v_nova) > parse(v_atual)
    except Exception:
        return False


class AtualizadorOTA:
    """Gerenciador de verificação, download e aplicação de atualizações OTA."""

    def __init__(self, versao_atual: str = VERSAO_ATUAL, url_servidor: str = ""):
        self.versao_atual = versao_atual
        self.url_servidor = url_servidor.strip()

    def verificar_atualizacao(self) -> Tuple[bool, str, Optional[dict]]:
        """
        Verifica se há atualizações disponíveis no servidor configurado.
        Retorna (sucesso, mensagem, dados_atualizacao).
        """
        if not self.url_servidor:
            return (
                False,
                "O serviço de atualização OTA está inativo porque nenhuma URL de servidor foi configurada.",
                None
            )

        try:
            req = urllib.request.Request(
                self.url_servidor,
                headers={"User-Agent": f"NfSplit-Updater/{self.versao_atual}"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status != 200:
                    return False, f"Servidor retornou status HTTP {response.status}.", None
                dados = json.loads(response.read().decode("utf-8"))

            versao_remota = dados.get("versao", "")
            if not versao_remota:
                return False, "Resposta do servidor não contém o campo 'versao'.", None

            if comparar_versoes(self.versao_atual, versao_remota):
                return (
                    True,
                    f"Nova versão {versao_remota} disponível!",
                    dados
                )
            else:
                return (
                    False,
                    f"Você já está utilizando a versão mais recente ({self.versao_atual}).",
                    dados
                )

        except urllib.error.URLError as e:
            return False, f"Não foi possível conectar ao servidor de atualização: {e.reason}", None
        except json.JSONDecodeError:
            return False, "O servidor retornou um formato inválido (não é JSON).", None
        except Exception as e:
            return False, f"Erro inesperado ao verificar atualizações: {str(e)}", None

    def baixar_atualizacao(
        self,
        url_download: str,
        sha256_esperado: str = "",
        callback_progresso: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[bool, str, Optional[Path]]:
        """
        Baixa o arquivo binário da nova versão para uma pasta temporária.
        Retorna (sucesso, mensagem, caminho_arquivo_baixado).
        """
        try:
            fd, temp_path_str = tempfile.mkstemp(prefix="NfSplit_update_", suffix=".exe")
            os.close(fd)
            temp_path = Path(temp_path_str)

            req = urllib.request.Request(
                url_download,
                headers={"User-Agent": f"NfSplit-Updater/{self.versao_atual}"}
            )

            hasher = hashlib.sha256() if sha256_esperado else None

            with urllib.request.urlopen(req, timeout=30) as resp:
                total_bytes = int(resp.headers.get("Content-Length", 0))
                bytes_baixados = 0
                bloco_tamanho = 64 * 1024

                with open(temp_path, "wb") as f_out:
                    while True:
                        bloco = resp.read(bloco_tamanho)
                        if not bloco:
                            break
                        f_out.write(bloco)
                        bytes_baixados += len(bloco)
                        if hasher:
                            hasher.update(bloco)
                        if callback_progresso and total_bytes > 0:
                            callback_progresso(bytes_baixados, total_bytes)

            # Validação opcional de integridade SHA-256
            if sha256_esperado:
                sha_calculado = hasher.hexdigest().lower()
                if sha_calculado != sha256_esperado.strip().lower():
                    temp_path.unlink(missing_ok=True)
                    return False, "Falha de integridade: SHA-256 do arquivo baixado não confere.", None

            return True, "Download concluído com sucesso!", temp_path

        except Exception as e:
            return False, f"Erro ao realizar download da atualização: {str(e)}", None

    @staticmethod
    def aplicar_atualizacao_ota(novo_exe: Path) -> Tuple[bool, str]:
        """
        Gera e executa script em lote para substituir o executável atual e reiniciar.
        """
        try:
            exe_atual = Path(sys.executable).resolve()
            if not getattr(sys, "frozen", False):
                return False, "A atualização OTA automática só pode ser aplicada a partir do arquivo compilado (.exe)."

            pid_atual = os.getpid()
            pasta_temp = Path(tempfile.gettempdir())
            bat_script = pasta_temp / f"ota_apply_{pid_atual}.bat"

            script_content = f"""@echo off
chcp 65001 > nul
echo Aguardando encerramento do processo antigo (PID: {pid_atual})...
timeout /t 2 /nobreak > nul

:loop_espera
tasklist /fi "PID eq {pid_atual}" 2>nul | find "{pid_atual}" >nul
if %errorlevel% equ 0 (
    timeout /t 1 /nobreak > nul
    goto loop_espera
)

echo Substituindo executavel por nova versao...
copy /y "{str(novo_exe)}" "{str(exe_atual)}" > nul
if %errorlevel% neq 0 (
    echo Erro ao copiar o novo arquivo.
    exit /b 1
)

del /f /q "{str(novo_exe)}" > nul

echo Reiniciando o NfSplit atualizado...
start "" "{str(exe_atual)}"

del /f /q "%~f0" > nul
exit
"""
            with open(bat_script, "w", encoding="utf-8") as f:
                f.write(script_content)

            # Dispara o instalador OTA em segundo plano
            subprocess.Popen(["cmd.exe", "/c", str(bat_script)], shell=True)
            # Encerra o processo atual para liberar o arquivo para substituição
            sys.exit(0)

        except Exception as e:
            return False, f"Falha ao iniciar processo de instalação OTA: {str(e)}"
