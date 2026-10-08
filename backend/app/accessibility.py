"""Bounded read-only Windows accessibility observation; no app-specific selectors."""
import json
import os
import subprocess


class ObservationChangedError(RuntimeError):
    """The desktop changed while collecting a frame; no input was dispatched."""


_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]__HANDLE__)
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$queue = [System.Collections.Generic.Queue[System.Windows.Automation.AutomationElement]]::new()
$queue.Enqueue($root)
$output = @()
$seen = 0
while ($queue.Count -gt 0 -and $seen -lt 180 -and $output.Count -lt 70) {
    $node = $queue.Dequeue(); $seen++
    try {
        $c = $node.Current; $r = $c.BoundingRectangle
        if (-not $c.IsOffscreen -and $c.IsEnabled -and -not $c.IsPassword -and $r.Width -gt 0 -and $r.Height -gt 0) {
            $role = $c.ControlType.ProgrammaticName
            if ($role -match 'Button|Edit|MenuItem|ListItem|Hyperlink|TabItem|CheckBox|ComboBox|RadioButton') {
                $name = $c.Name
                if ($name.Length -gt 100) { $name = $name.Substring(0,100) }
                $output += @{name=$name; role=$role; rect=@($r.X,$r.Y,$r.Width,$r.Height); runtime_id=($node.GetRuntimeId() -join '.')}
            }
        }
        $child = $walker.GetFirstChild($node)
        while ($null -ne $child -and $queue.Count -lt 180) {
            $queue.Enqueue($child); $child = $walker.GetNextSibling($child)
        }
    } catch { }
}
ConvertTo-Json -InputObject @($output) -Depth 4 -Compress
'''


def read_targets(window_id):
    if os.name != 'nt' or not window_id:
        return []
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                                 _SCRIPT.replace('__HANDLE__', str(int(window_id)))],
                                capture_output=True, encoding='utf-8', errors='replace',
                                timeout=3, creationflags=0x08000000)
        if result.returncode:
            return []
        data = json.loads(result.stdout)
        return [item for item in data[:70] if isinstance(item, dict)] if isinstance(data, list) else []
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return []  # Opaque or unresponsive apps retain the visual fallback.
