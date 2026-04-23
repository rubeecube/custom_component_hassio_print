#!/usr/bin/env bash
# Starts CUPS and registers a cups-pdf virtual printer called "TestPrinter".
# cups-pdf saves every job as a PDF under /var/spool/cups-pdf/ANONYMOUS/.

set -euo pipefail

# ------------------------------------------------------------------
# 1. Start CUPS in the background
# ------------------------------------------------------------------
/usr/sbin/cupsd -f &
CUPSD_PID=$!

# ------------------------------------------------------------------
# 2. Wait until CUPS is accepting connections
# ------------------------------------------------------------------
echo "Waiting for CUPS to start..."
for i in $(seq 1 30); do
    if lpstat -h localhost -r 2>/dev/null; then
        echo "CUPS is ready."
        break
    fi
    sleep 1
done

# ------------------------------------------------------------------
# 3. Register the cups-pdf virtual printer as "TestPrinter"
# ------------------------------------------------------------------
if ! lpstat -h localhost -p TestPrinter 2>/dev/null | grep -q TestPrinter; then
    echo "Registering TestPrinter (cups-pdf)..."
    lpadmin \
        -h localhost \
        -p TestPrinter \
        -v cups-pdf:/ \
        -m lsb/usr/cups-pdf/CUPS-PDF_opt.ppd \
        -E \
        -o media=A4 \
        -o sides=two-sided-long-edge
    cupsenable -h localhost TestPrinter
    cupsaccept -h localhost TestPrinter
    echo "TestPrinter registered."
else
    echo "TestPrinter already registered."
fi

# ------------------------------------------------------------------
# 4. Hand off to CUPS (foreground)
# ------------------------------------------------------------------
wait "$CUPSD_PID"
