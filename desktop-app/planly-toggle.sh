#!/bin/bash
PID=$(cat /tmp/planly.pid 2>/dev/null)
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  kill -USR1 "$PID"
fi
