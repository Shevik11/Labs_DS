import ctypes as C
import shutil
import subprocess
from pathlib import Path

ROOT=Path(r'D:\LNU\DS\8\.tools\report-render')
DLL=C.WinDLL('msi')
H=C.c_uint
DLL.MsiOpenDatabaseW.argtypes=[C.c_wchar_p,C.c_void_p,C.POINTER(H)]
DLL.MsiDatabaseOpenViewW.argtypes=[H,C.c_wchar_p,C.POINTER(H)]
DLL.MsiViewExecute.argtypes=[H,H]
DLL.MsiViewFetch.argtypes=[H,C.POINTER(H)]
DLL.MsiRecordGetStringW.argtypes=[H,H,C.c_wchar_p,C.POINTER(H)]
DLL.MsiRecordReadStream.argtypes=[H,H,C.c_void_p,C.POINTER(H)]
DLL.MsiCloseHandle.argtypes=[H]

def ok(code):
    if code:raise OSError(code)

def value(record,column):
    size=H(0)
    result=DLL.MsiRecordGetStringW(record,column,None,C.byref(size))
    if result not in (0,234):ok(result)
    buffer=C.create_unicode_buffer(size.value+1)
    capacity=H(len(buffer))
    ok(DLL.MsiRecordGetStringW(record,column,buffer,C.byref(capacity)))
    return buffer.value

database=H()
ok(DLL.MsiOpenDatabaseW(str(ROOT/'LibreOffice.msi'),None,C.byref(database)))

def query(sql,columns):
    view=H();ok(DLL.MsiDatabaseOpenViewW(database,sql,C.byref(view)));ok(DLL.MsiViewExecute(view,0))
    rows=[]
    while True:
        record=H();result=DLL.MsiViewFetch(view,C.byref(record))
        if result==259:break
        ok(result);rows.append(tuple(value(record,i+1) for i in range(columns)));DLL.MsiCloseHandle(record)
    DLL.MsiCloseHandle(view)
    return rows

raw=ROOT/'cabfiles';raw.mkdir(exist_ok=True)
for (cabinet,) in query('SELECT `Cabinet` FROM `Media`',1):
    if not cabinet:continue
    if not cabinet.startswith('#'):raise RuntimeError('Expected embedded cabinet')
    name=cabinet[1:]
    view=H();ok(DLL.MsiDatabaseOpenViewW(database,"SELECT `Data` FROM `_Streams` WHERE `Name`='"+name+"'",C.byref(view)))
    ok(DLL.MsiViewExecute(view,0));record=H();ok(DLL.MsiViewFetch(view,C.byref(record)))
    cab=ROOT/Path(name).name
    with cab.open('wb') as output:
        buffer=C.create_string_buffer(65536)
        while True:
            length=H(len(buffer));ok(DLL.MsiRecordReadStream(record,1,buffer,C.byref(length)))
            if not length.value:break
            output.write(buffer.raw[:length.value])
    DLL.MsiCloseHandle(record);DLL.MsiCloseHandle(view)
    with (ROOT/'cab-expand.log').open('w',encoding='utf-8') as log:
        subprocess.run(['C:/Windows/System32/expand.exe','-F:*',str(cab),str(raw)],stdout=log,stderr=subprocess.STDOUT,check=True)
components={key:directory for key,directory in query('SELECT `Component`, `Directory_` FROM `Component`',2)}
directories={key:(parent,default) for key,parent,default in query('SELECT `Directory`, `Directory_Parent`, `DefaultDir` FROM `Directory`',3)}
target=ROOT/'LibreOffice-readonly';target.mkdir(exist_ok=True)

def directory_path(key):
    parent,default=directories[key]
    if not parent:return Path()
    name=default.split(':',1)[0].split('|')[-1]
    return directory_path(parent)/(name if name!='.' else '')

missing=[];count=0;executables=[]
for key,component,name in query('SELECT `File`, `Component_`, `FileName` FROM `File`',3):
    source=raw/key
    if not source.exists():missing.append(key);continue
    name=name.split('|')[-1]
    dest=target/directory_path(components[component])/name
    if not dest.resolve().is_relative_to(target.resolve()):raise RuntimeError('Unexpected cabinet destination')
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.move(str(source),str(dest));count+=1
    if name.lower()=='soffice.exe':executables.append(str(dest))
DLL.MsiCloseHandle(database)
print('Extracted files:',count,'Missing:',len(missing),'LibreOffice:',executables)
if missing or not executables:raise RuntimeError('Incomplete read-only MSI extraction')
(ROOT/'soffice-path.txt').write_text(executables[0],encoding='utf-8')
