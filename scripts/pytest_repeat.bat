set COUNTER=0

echo "Executing %2 repetitions for tests: %1"

:repeat
set /A COUNTER=COUNTER+1
echo "Executing repetition: %COUNTER%"

pytest %1 || goto :fail

if %COUNTER% == %2 (
   goto :pass
) else (
   goto :repeat
)

:pass
rundll32 user32.dll,MessageBeep
msg console /time:3600 "All tests passed successfully after %COUNTER% runs"
exit /B 0

:fail
rundll32 user32.dll,MessageBeep
msg console /time:3600 "Tests failed after %COUNTER% runs"
exit /B 1
