from pathlib import Path
import ctypes as C,json
ROOT=Path(r'D:\LNU\DS\8\.tools\report-render')
source=Path(r'D:\LNU\DS\8\work\report\extract_renderer.py').read_text(encoding='utf-8')
# Reuse the read-only MSI table and embedded stream reader.
setup=source[:source.index('raw=ROOT/')]
exec(compile(setup,'read_only_msi','exec'))
components={k:d for k,d in query('SELECT `Component`, `Directory_` FROM `Component`',2)}
directories={k:(p,n) for k,p,n in query('SELECT `Directory`, `Directory_Parent`, `DefaultDir` FROM `Directory`',3)}
def directory_path(key):
    parent,default=directories[key]
    if not parent:return Path()
    name=default.split(':',1)[0].split('|')[-1]
    return directory_path(parent)/(name if name!='.' else '')
target=ROOT/'LibreOffice-readonly';target.mkdir(exist_ok=True)
files={};total=0
for key,component,name,size in query('SELECT `File`, `Component_`, `FileName`, `FileSize` FROM `File`',4):
    relative=directory_path(components[component])/name.split('|')[-1]
    normalized=relative.as_posix().lower()
    if any(v in normalized for v in ['/help/','/readmes/','/sdk/','/share/gallery/','/share/extensions/','/share/template/','/share/autotext/','/share/wizards/','/program/python-core-']):continue
    dest=target/relative
    if not dest.resolve().is_relative_to(target.resolve()):raise ValueError(dest)
    files[key]=str(dest);total+=int(size)
print('Selected files:',len(files),'bytes:',total,flush=True)
cabinets=[]
for (cabinet,) in query('SELECT `Cabinet` FROM `Media`',1):
    if not cabinet:continue
    assert cabinet.startswith('#');name=cabinet[1:];cab=ROOT/Path(name).name
    view=H();ok(DLL.MsiDatabaseOpenViewW(database,"SELECT `Data` FROM `_Streams` WHERE `Name`='"+name+"'",C.byref(view)))
    ok(DLL.MsiViewExecute(view,0));record=H();ok(DLL.MsiViewFetch(view,C.byref(record)))
    with cab.open('wb') as output:
        buffer=C.create_string_buffer(65536)
        while True:
            length=H(len(buffer));ok(DLL.MsiRecordReadStream(record,1,buffer,C.byref(length)))
            if not length.value:break
            output.write(buffer.raw[:length.value])
    DLL.MsiCloseHandle(record);DLL.MsiCloseHandle(view);cabinets.append(cab)
DLL.MsiCloseHandle(database)
(ROOT/'selected_files.json').write_text(json.dumps(files),encoding='utf-8')
(ROOT/'LibreOffice.msi').unlink()
class CabinetFile(C.Structure):
    _fields_=[('NameInCabinet',C.c_wchar_p),('FileSize',C.c_uint32),('Win32Error',C.c_uint32),('DosDate',C.c_uint16),('DosTime',C.c_uint16),('DosAttribs',C.c_uint16),('FullTargetName',C.c_wchar*260)]
CALLBACK=C.WINFUNCTYPE(C.c_uint,C.c_void_p,C.c_uint,C.c_size_t,C.c_size_t)
errors=[];extracted=0
@CALLBACK
def callback(context,notification,param1,param2):
    global extracted
    try:
        if notification==0x11:
            info=C.cast(param1,C.POINTER(CabinetFile)).contents
            dest=files.get(info.NameInCabinet)
            if not dest:return 2
            Path(dest).parent.mkdir(parents=True,exist_ok=True)
            info.FullTargetName=dest;extracted+=1
            return 1
        if notification==0x13:return 0
        if notification==0x12:errors.append('Unexpected additional cabinet');return 0
        return 0
    except Exception as e:errors.append(repr(e));return 0
api=C.WinDLL('setupapi',use_last_error=True)
api.SetupIterateCabinetW.argtypes=[C.c_wchar_p,C.c_uint,CALLBACK,C.c_void_p]
api.SetupIterateCabinetW.restype=C.c_int
for cab in cabinets:
    if not api.SetupIterateCabinetW(str(cab),0,callback,None):raise C.WinError(C.get_last_error())
    cab.unlink()
assert not errors,errors
missing=[v for v in files.values() if not Path(v).exists()]
assert not missing,missing[:10]
exe=next(target.rglob('soffice.exe'))
(ROOT/'soffice-path.txt').write_text(str(exe),encoding='utf-8')
print('Extracted',extracted,'files. Renderer:',exe,flush=True)
