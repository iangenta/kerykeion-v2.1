from matplotlib import font_manager 

def get_font(name):
    font_path = font_manager.findfont(font_manager.FontProperties(family=name))
    font_props = font_manager.FontProperties(fname=font_path)
    font_name = font_props.get_name()
    return font_name

installed_fonts = font_manager.findSystemFonts()
sorted_fonts = sorted(installed_fonts, key=lambda x: font_manager.FontProperties(fname=x).get_name())

font_dirs = ["fonts"]
font_files = font_manager.findSystemFonts(fontpaths=font_dirs)
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)


font_list = font_manager.get_font_names()
sorted_font_list = sorted(font_list)
for x in sorted_font_list:
    print(x)

