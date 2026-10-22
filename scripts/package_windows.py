"""Package only the frozen application, never workspace/user data."""
import hashlib
from pathlib import Path
import time
import zipfile

root = Path(__file__).resolve().parents[1]
folder = root / 'dist' / 'ExchangeStudio'
archive = root / 'dist' / 'ExchangeStudio-Windows.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
    for path in sorted(folder.rglob('*')):
        if path.is_file():
            for attempt in range(5):
                try:
                    content = path.read_bytes()
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(.5)
            output.writestr(path.relative_to(folder.parent).as_posix(), content)
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(root / 'dist' / 'SHA256SUMS.txt').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
print(f'Built: {archive} ({archive.stat().st_size:,} bytes)')
