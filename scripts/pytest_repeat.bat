set COUNTER=0

set COUNTER_MAX=%1
for /F "Tokens=1*" %%A in ("%*") do set "PYTEST_ARGS=%%B"

echo "Executing %COUNTER_MAX% repetitions for tests: %PYTEST_ARGS%"

:repeat
set /A COUNTER=COUNTER+1
echo "Executing repetition: %COUNTER%"

pytest %PYTEST_ARGS% || goto :fail

if %COUNTER% == %COUNTER_MAX% (
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
