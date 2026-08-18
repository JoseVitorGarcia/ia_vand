#!/usr/bin/env bash
# Roda o pipeline num cgroup próprio, fora do scope do VSCode.
#
# Por quê: o terminal integrado do VSCode vive no scope systemd
# app-code-<pid>.scope, que tem OOMPolicy=stop — quando o kernel mata o python
# por OOM, o systemd derruba o scope inteiro e o editor fecha junto.
# Rodando aqui dentro, o OOM fica contido neste cgroup e o VSCode sobrevive.
#
# Uso:
#   ./run.sh                    # roda main.py com limite de 8G
#   ./run.sh -m pytest tests    # roda qualquer coisa com o python do venv
#   MEM_MAX=6G ./run.sh         # ajusta o teto de memória
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$RAIZ/venv/bin/python"
MEM_MAX="${MEM_MAX:-8G}"
SWAP_MAX="${SWAP_MAX:-512M}"

if [[ ! -x "$PY" ]]; then
    echo "run.sh: python do venv não encontrado em $PY" >&2
    exit 1
fi

if [[ $# -eq 0 ]]; then
    set -- "$RAIZ/main.py"
fi

cd "$RAIZ"
# Deixa `import src` funcionar mesmo para scripts de fora do projeto
export PYTHONPATH="$RAIZ${PYTHONPATH:+:$PYTHONPATH}"

if ! command -v systemd-run >/dev/null 2>&1; then
    echo "run.sh: systemd-run indisponível — rodando sem isolamento (o editor pode fechar em caso de OOM)" >&2
    exec "$PY" "$@"
fi

echo "run.sh: scope isolado (MemoryMax=$MEM_MAX, MemorySwapMax=$SWAP_MAX)" >&2

set +e
systemd-run --user --scope --quiet \
    --unit="ia-vand-$$" \
    -p MemoryMax="$MEM_MAX" \
    -p MemorySwapMax="$SWAP_MAX" \
    "$PY" "$@"
codigo=$?
set -e

if [[ $codigo -eq 137 ]]; then
    echo "" >&2
    echo "run.sh: o processo foi morto por OOM ao bater em $MEM_MAX." >&2
    echo "        O VSCode sobreviveu porque o estouro ficou contido neste cgroup." >&2
    echo "        Veja o pico real com: journalctl --user -n 20 | grep -i 'ia-vand'" >&2
fi

exit $codigo
