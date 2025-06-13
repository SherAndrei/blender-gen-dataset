## Frequently Asked Questions

### Q: How do I force CPU on headless systems like WSL?  
**A**: On headless systems, you need to set these environment variables to force CPU rendering:  
```bash
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
```

### Q: Does Blender support in-memory rendering to avoid I/O operations?  
**A**: As it seems, there is no native support for keeping rendering results purely in memory. See these references:  
- [StackOverflow answer](https://stackoverflow.com/a/58948767/15751315)  
- [Blender DevTalk thread](https://devtalk.blender.org/t/is-it-possible-to-store-keep-the-rendering-result-in-memory-only-and-avoid-doing-i-o/11852/2)  
- [Blender StackExchange](https://blender.stackexchange.com/q/289920)  

### Q: How can I improve rendering performance without in-memory support?  
**A**: Using a RAM disk is recommended:  

**Linux**:  
```bash
sudo mkdir -p /media/generatormeta
sudo mount -t tmpfs -o size=1024M tmpfs /media/generatormeta/
```  
([Tutorial reference](https://web.archive.org/web/20180123110848/http://ubuntublog.org/tutorials/how-to-create-ramdisk-linux.htm))  

**Windows**:  
Use [ImDisk Toolkit](https://imdisktoolkit.com/) to create a RAM disk.  

### Q: Can I use my system Python instead of Blender's embedded Python interpreter?  
**A**: By default, the script uses Blender's embedded Python interpreter for version compatibility. However, there are alternative approaches:  

1. **Using System Python**:  
   You can configure Blender to use your system Python installation by following [Blender's documentation on bundled Python extensions](https://docs.blender.org/api/current/info_tips_and_tricks.html#bundled-python-extensions).  

2. **Building Blender as Python Module**:  
   For advanced use cases, you can build Blender as a Python module to use within your system Python environment. See the [build documentation](https://developer.blender.org/docs/handbook/building_blender/python_module/) for instructions.
