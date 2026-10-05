<#
.SYNOPSIS
    Moves the mouse 5 px to the right and back again, once a minute.

.DESCRIPTION
    The cursor hops 5 px right and, a moment later, returns to exactly where it was.
    A real mouse-input event is also reported to Windows, so it counts as activity
    (screen saver, auto-lock, Teams/Slack "Away"). If you're using the mouse at that
    moment, it is left alone instead of being yanked back.

    Stop with Ctrl+C or by closing the window.

.EXAMPLE
    .\mouse-jiggler.ps1
.EXAMPLE
    .\mouse-jiggler.ps1 -Pixels 10 -IntervalSeconds 30
#>
param(
    [int]$Pixels = 5,
    [int]$IntervalSeconds = 60
)

Add-Type -Namespace Win32 -Name Mouse -MemberDefinition @'
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int X; public int Y; }

    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT point);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, int dx, int dy, uint data, UIntPtr extraInfo);
    [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
'@

# Use physical pixels so the cursor returns to the exact same spot on scaled / multi-monitor setups.
try { [void][Win32.Mouse]::SetThreadDpiAwarenessContext([IntPtr](-4)) } catch { }

$MOUSEEVENTF_MOVE = 0x0001
$start = New-Object Win32.Mouse+POINT
$now   = New-Object Win32.Mouse+POINT

Write-Host "Moving the mouse $Pixels px right and back every $IntervalSeconds s. Press Ctrl+C to stop."

while ($true) {
    if ([Win32.Mouse]::GetCursorPos([ref]$start)) {    # fails while the PC is locked
        [void][Win32.Mouse]::SetCursorPos($start.X + $Pixels, $start.Y)

        # SetCursorPos isn't reported as user input, so on its own it won't keep the PC awake.
        # A zero-length mouse move sent as real input is what resets the idle timer.
        [Win32.Mouse]::mouse_event($MOUSEEVENTF_MOVE, 0, 0, 0, [UIntPtr]::Zero)

        Start-Sleep -Milliseconds 200

        # Move back - unless you moved the mouse yourself in the meantime.
        if ([Win32.Mouse]::GetCursorPos([ref]$now) -and $now.X -eq $start.X + $Pixels -and $now.Y -eq $start.Y) {
            [void][Win32.Mouse]::SetCursorPos($start.X, $start.Y)
        }

        Write-Host -NoNewline "`rLast move: $(Get-Date -Format 'HH:mm:ss')"
    }
    Start-Sleep -Seconds $IntervalSeconds
}
