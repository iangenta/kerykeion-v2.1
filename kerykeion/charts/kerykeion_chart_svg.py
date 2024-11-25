# -*- coding: utf-8 -*-
"""
    This is part of Kerykeion (C) 2023 Giacomo Battaglia
"""
import math
import pytz
import logging
from matplotlib import font_manager
from datetime import datetime
from kerykeion.settings.kerykeion_settings import get_settings
from kerykeion.aspects.synastry_aspects import SynastryAspects
from kerykeion.aspects.natal_aspects import NatalAspects
from kerykeion.astrological_subject import AstrologicalSubject
from kerykeion.kr_types import KerykeionException, ChartType
from kerykeion.kr_types import ChartTemplateDictionary
from kerykeion.charts.charts_utils import decHourJoin, degreeDiff, offsetToTz, sliceToX, sliceToY
from pathlib import Path
from string import Template
from typing import Union


font_dir = Path(__file__).resolve().parent / 'fonts'
font_files = font_manager.findSystemFonts(fontpaths=str(font_dir))
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)

class KerykeionChartSVG:
    """
    Creates the instance that can generate the chart with the
    function makeSVG().

    Parameters:
        - first_obj: First kerykeion object
        - chart_type: Natal, ExternalNatal, Transit, Synastry (Default: Type="Natal").
        - second_obj: Second kerykeion object (Not required if type is Natal)
        - new_output_directory: Set the output directory (default: output_directory)
        - lang: language settings (default: "EN")
        - new_settings_file: Set the settings file, receive "dark" or "bright"
        - new_bg_color: hexadecimal color
        - new_bg_image: image URL
        - new_bg_image_wheel: image URL
        
    """

    first_obj: AstrologicalSubject
    second_obj: Union[AstrologicalSubject, None]
    chart_type: ChartType
    new_output_directory: Union[Path, None]
    new_settings_file: Union[Path, None]
    output_directory: Path
    new_font: Union[str, None]
    new_font_name: Union[str, None]
    new_bg_color: Union[str, None]
    new_bg_image: Union[str, None]
    new_bg_image_wheel: Union[str, None]
    name_spacing:bool
    def __init__(
        self,
        first_obj: AstrologicalSubject,
        chart_type: ChartType = "Natal",
        second_obj: Union[AstrologicalSubject, None] = None,
        new_output_directory: Union[str, None] = None,
        new_settings_file: Union[Path, None] = None,
        new_font: Union[str, None] = "Belgan Aesthetic",
        new_font_name: Union[str, None] = "Belgan Aesthetic",
        new_bg_color: Union[str, None] = None,
        new_bg_image: Union[str, None] = None,
        new_bg_image_wheel: Union[str, None] = None,
        name_spacing:bool = False,
    ):
        # Directories:
        DATA_DIR = Path(__file__).parent
        self.homedir = Path.home()
        self.new_settings_file = new_settings_file

        #name_spacing
        for char in first_obj.name:
            if char in ['j', 'q', 'g', 'p']:
                name_spacing = True
                print(char)
                break
        else:
            name_spacing = False

        self.name_spacing = name_spacing
                
        #Font:
        if new_font is not None:
            self.font = self.get_font(new_font)
        else:
            self.font = "Belgan Aesthetic"
            
        if new_font_name is not None:
            self.font_name = self.get_font(new_font_name)
        else:
            self.font_name = "Belgan Aesthetic"
        
        #bg_color
        if new_bg_color is not None:
            self.bg_color = new_bg_color
        else:
            self.bg_color = None

        #bg_image
        if new_bg_image is not None:
            x09 = "0"
            y09 = "0"
            w09 = "650.4245745"
            h09 = "100%"
            n09 = "none"
            self.bg_image = f'<image x="{x09}" y="{y09}" width="{w09}" height="{h09}" xlink:href="{new_bg_image}" preserveAspectRatio="{n09}"/>'
        else:
            self.bg_image = "<symbol></symbol>"

        #bg_image_wheel
        if new_bg_image_wheel is not None:
            self.bg_image_wheel = new_bg_image_wheel
            self.bg_image_wheel_is_active = True
            self.bg_image_wheel_pattern = f"<defs><pattern id=\"image\" x=\"0\" y=\"0\" width=\"100%\" height=\"100%\" patternContentUnits=\"objectBoundingBox\"><image xlink:href=\"{new_bg_image_wheel}\" width=\"1\" height=\"1\" preserveAspectRatio=\"xMidYMid slice\" /></pattern></defs>"
        else:
            self.bg_image_wheel = new_bg_image_wheel
            self.bg_image_wheel_is_active = False
            self.bg_image_wheel_pattern = ""
            
        #for c1 pattern
        self.offset = 0
        # new output directory
        if new_output_directory:
            self.output_directory = Path(new_output_directory)
        else:
            self.output_directory = self.homedir

        self.xml_svg = DATA_DIR / "templates/chart.xml"
        self.natal_width = 650.4245745 # Width of A4 in points (72 points per inch)
        self.full_width = 650.4245745 # Full width for A4 format
        
            
        self.parse_json_settings(self.new_settings_file)
        self.chart_type = chart_type

        # Kerykeion instance
        self.user = first_obj

        self.available_planets_setting = []
        for body in self.planets_settings:
            if body['is_active'] == False:
                continue

            self.available_planets_setting.append(body)
            
        # Available bodies
        available_celestial_points = []
        for body in self.available_planets_setting:
            available_celestial_points.append(body["name"].lower())
        
        # Make a list for the absolute degrees of the points of the graphic.
        self.points_deg_ut = []
        for planet in available_celestial_points:
            self.points_deg_ut.append(self.user.get(planet).abs_pos)

        # Make a list of the relative degrees of the points in the graphic.
        self.points_deg = []
        for planet in available_celestial_points:
            self.points_deg.append(self.user.get(planet).position)

        # Make list of the points sign
        self.points_sign = []
        for planet in available_celestial_points:
            self.points_sign.append(self.user.get(planet).sign_num)

        # Make a list of points if they are retrograde or not.
        self.points_retrograde = []
        for planet in available_celestial_points:
            self.points_retrograde.append(self.user.get(planet).retrograde)

        # Makes the sign number list.

        self.houses_sign_graph = []
        for h in self.user.houses_list:
            self.houses_sign_graph.append(h["sign_num"])

        if self.chart_type == "Natal" or self.chart_type == "ExternalNatal":
            natal_aspects_instance = NatalAspects(self.user, new_settings_file=self.new_settings_file)
            self.aspects_list = natal_aspects_instance.relevant_aspects

        # TODO: If not second should exit
        if self.chart_type == "Transit" or self.chart_type == "Synastry":
            if not second_obj:
                raise KerykeionException("Second object is required for Transit or Synastry charts.")

            # Kerykeion instance
            self.t_user = second_obj

            # Make a list for the absolute degrees of the points of the graphic.
            self.t_points_deg_ut = []
            for planet in available_celestial_points:            
                self.t_points_deg_ut.append(self.t_user.get(planet).abs_pos)

            # Make a list of the relative degrees of the points in the graphic.
            self.t_points_deg = []
            for planet in available_celestial_points:
                self.t_points_deg.append(self.t_user.get(planet).position)

            # Make list of the poits sign.
            self.t_points_sign = []
            for planet in available_celestial_points:
                self.t_points_sign.append(self.t_user.get(planet).sign_num)

            # Make a list of poits if they are retrograde or not.
            self.t_points_retrograde = []
            for planet in available_celestial_points:
                self.t_points_retrograde.append(self.t_user.get(planet).retrograde)

            self.t_houses_sign_graph = []
            for h in self.t_user.houses_list:
                self.t_houses_sign_graph.append(h["sign_num"])

        # screen size
        if self.chart_type == "Natal":
            self.screen_width = 650.4245745
        else:
            self.screen_width = 650.4245745
        self.screen_height = 1200

        # check for home
        self.home_location = self.user.city
        self.home_geolat = self.user.lat
        self.home_geolon = self.user.lng
        self.home_countrycode = self.user.nation
        self.home_timezonestr = self.user.tz_str

        logging.info(f"{self.user.name} birth location: {self.home_location}, {self.home_geolat}, {self.home_geolon}")

        # default location
        self.location = self.home_location
        self.geolat = float(self.home_geolat)
        self.geolon = float(self.home_geolon)
        self.countrycode = self.home_countrycode
        self.timezonestr = self.home_timezonestr

        # current datetime
        now = datetime.now()

        # aware datetime object
        dt_input = datetime(now.year, now.month, now.day, now.hour, now.minute, now.second)
        dt = pytz.timezone(self.timezonestr).localize(dt_input)

        # naive utc datetime object
        dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()  # type: ignore

        # Default
        self.name = self.user.name
        self.charttype = self.chart_type
        self.year = self.user.utc.year
        self.month = self.user.utc.month
        self.day = self.user.utc.day
        self.hour = self.user.utc.hour + self.user.utc.minute / 100
        self.timezone = offsetToTz(dt.utcoffset())
        self.altitude = 25
        self.geonameid = None

        # Transit

        if self.chart_type == "Transit":
            self.t_geolon = self.geolon
            self.t_geolat = self.geolat
            self.t_altitude = self.altitude
            self.t_name = self.language_settings["transit_name"]
            self.t_year = dt_utc.year
            self.t_month = dt_utc.month
            self.t_day = dt_utc.day
            self.t_hour = decHourJoin(dt_utc.hour, dt_utc.minute, dt_utc.second)
            self.t_timezone = offsetToTz(dt.utcoffset())
            self.t_altitude = 25
            self.t_geonameid = None

        # configuration
        # ZOOM 1 = 100%
        self.zoom = 1

        self.zodiac = (
            {"name": "aries", "element": "fire"},
            {"name": "taurus", "element": "earth"},
            {"name": "gemini", "element": "air"},
            {"name": "cancer", "element": "water"},
            {"name": "leo", "element": "fire"},
            {"name": "virgo", "element": "earth"},
            {"name": "libra", "element": "air"},
            {"name": "scorpio", "element": "water"},
            {"name": "sagittarius", "element": "fire"},
            {"name": "capricorn", "element": "earth"},
            {"name": "aquarius", "element": "air"},
            {"name": "pisces", "element": "water"},
        )

        # Immediately generate template.
        self.template = self.makeTemplate()

    def get_font(self, new_font_name):
        """
        Sets the font and return it's name
        """
        font_path = font_manager.findfont(font_manager.FontProperties(family=new_font_name))
        font_props = font_manager.FontProperties(fname=font_path)
        font_name = font_props.get_name()
        if font_name == new_font_name:
            return font_name
        else:
            font_name = "Belgan Aesthetic"
            return font_name
    
    def set_output_directory(self, dir_path: Path) -> None:
        """
        Sets the output direcotry and returns it's path.
        """
        self.output_directory = dir_path
        logging.info(f"Output direcotry set to: {self.output_directory}")

    def parse_json_settings(self, settings_file):
        """
        Parse the settings file.
        """
        settings = get_settings(settings_file)

        language = settings["general_settings"]["language"]
        self.language_settings = settings["language_settings"].get(language, "EN")
        self.chart_colors_settings = settings["chart_colors"]
        self.planets_settings = settings["celestial_points"]
        self.aspects_settings = settings["aspects"]
        self.planet_in_zodiac_extra_points = settings["general_settings"]["planet_in_zodiac_extra_points"]
        self.chart_settings = settings["chart_settings"]

    def _transitRing(self, r) -> str:
        """
        Draws the transit ring.
        """
        radius_offset = 18

        out = f'<circle cx="{r}" cy="{r}" r="{r - radius_offset}" style="fill: none; stroke: {self.chart_colors_settings["paper_1"]}; stroke-width: 36px; stroke-opacity: .4;"/>'
        out += f'<circle cx="{r}" cy="{r}" r="{r}" style="fill: none; stroke: {self.chart_colors_settings["zodiac_transit_ring_3"]}; stroke-width: 1px; stroke-opacity: .6;"/>'

        return out

    def _degreeRing(self, r) -> str:
        """
        Draws the degree ring.
        """
        out = ""
        for i in range(180):
            offset = float(i*2) - self.user.houses_degree_ut[6]
            if offset < 0:
                offset = offset + 360.0
            elif offset > 360:
                offset = offset - 360.0
            
            rad_1= 25   
            x1 = sliceToX(0, r- 4  - (self.c1+rad_1), offset) +4+ (self.c1+rad_1) 
            y1 = sliceToY(0, r- 4 - (self.c1+rad_1), offset) +4+ (self.c1+rad_1)
            x2 = sliceToX(0, r + 4 - (self.c1+rad_1), offset) - 4 + (self.c1+rad_1) 
            y2 = sliceToY(0, r + 4 - (self.c1+rad_1), offset) - 4 + (self.c1+rad_1) 

            out += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="stroke:{self.chart_colors_settings["paper_0"]}; stroke-width: 1px; stroke-opacity:1;"/>'


            rad2= 10
            x1b = sliceToX(0, r- 4  - (self.c1+rad2), offset) +4+ (self.c1+rad2)
            y1b = sliceToY(0, r- 4 - (self.c1+rad2), offset) +4+ (self.c1+rad2)
            x2b = sliceToX(0, r + 4 - (self.c1+rad2), offset) - 4 + (self.c1+rad2)
            y2b = sliceToY(0, r + 4 - (self.c1+rad2), offset) - 4 + (self.c1+rad2)
            
            out += f'<line x1="{x1b}" y1="{y1b}" x2="{x2b}" y2="{y2b}" style="stroke:{self.chart_colors_settings["paper_0"]}; stroke-width: 1px; stroke-opacity:1;"/>'
        return out

    def _degreeTransitRing(self, r):
        out = ""
        for i in range(360):
            offset = float(i*2) - self.user.houses_degree_ut[6]
            if offset < 0:
                offset = offset + 360.0
            elif offset > 360:
                offset = offset - 360.0
            x1 = sliceToX(0, r, offset)
            y1 = sliceToY(0, r, offset)
            x2 = sliceToX(0, r + 2, offset) - 2
            y2 = sliceToY(0, r + 2, offset) - 2
            out += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="stroke: #F00; stroke-width: 1px; stroke-opacity:.9;"/>'

        return out
     
    def _lat2str(self, coord):
        """Converts a floating point latitude to string with
        degree, minutes and seconds and the appropriate sign
        (north or south). Eg. 52.1234567 -> 52°7'25" N

        Args:
            coord (float): latitude in floating point format
        Returns:
            str: latitude in string format with degree, minutes,
             seconds and sign (N/S)
        """

        sign = self.language_settings["north"]
        if coord < 0.0:
            sign = self.language_settings["south"]
            coord = abs(coord)
        deg = int(coord)
        min = int((float(coord) - deg) * 60)
        sec = int(round(float(((float(coord) - deg) * 60) - min) * 60.0))
        return f"{deg}{(sign[0]).lower()}{min} "

    def _lon2str(self, coord):
        """Converts a floating point longitude to string with
        degree, minutes and seconds and the appropriate sign
        (east or west). Eg. 52.1234567 -> 52°7'25" E

        Args:
            coord (float): longitude in floating point format
        Returns:
            str: longitude in string format with degree, minutes,
                seconds and sign (E/W)
        """

        sign = self.language_settings["east"]
        if coord < 0.0:
            sign = self.language_settings["west"]
            coord = abs(coord)
        deg = int(coord)
        min = int((float(coord) - deg) * 60)
        sec = int(round(float(((float(coord) - deg) * 60) - min) * 60.0))
        return f"{deg}{(sign[0]).lower()}{min}"

    def _dec2deg(self, dec, type="3"):
        """Coverts decimal float to degrees in format
        a°b'c".
        """

        dec = float(dec)
        a = int(dec)
        a_new = (dec - float(a)) * 60.0
        b_rounded = int(round(a_new))
        b = int(a_new)
        c = int(round((a_new - float(b)) * 60.0))
        if type == "3":
            out = f"{a:02d}&#176;{b:02d}&#39;{c:02d}&#34;"
        elif type == "2":
            out = f"{a:02d}&#176;{b_rounded:02d}&#39;"
        elif type == "1":
            out = f"{a:02d}&#176;"
        else:
            raise KerykeionException(f"Wrong type: {type}, it must be 1, 2 or 3.")
        return str(out)

    def _drawAspect(self, r, ar, degA, degB, color):
        """
        Draws svg aspects: ring, aspect ring, degreeA degreeB
        """
        offset = (int(self.user.houses_degree_ut[6]) / -1) + int(degA)
        x1 = sliceToX(0, ar, offset) + (r - ar)
        y1 = sliceToY(0, ar, offset) + (r - ar)
        offset = (int(self.user.houses_degree_ut[6]) / -1) + int(degB)
        x2 = sliceToX(0, ar, offset) + (r - ar)
        y2 = sliceToY(0, ar, offset) + (r - ar)
        out = f'            <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="stroke: {color}; stroke-width: 0.7; stroke-opacity: 1;"/>'

        return out

    def _zodiacSlice(self, num, r, style, type):
        # pie slices
        offset = 360 - self.user.houses_degree_ut[6]
        # check transit
        if self.chart_type == "Transit" or self.chart_type == "Synastry":
            dropin = 0
        else:
            dropin = self.c1 
        slice = f'<path d="M{str(r)},{str(r)} L{str(dropin + sliceToX(num, r - dropin, offset))},{str(dropin + sliceToY(num, r - dropin, offset))} A{str(r - dropin)},{str(r - dropin)} 0 0,0 {str(dropin + sliceToX(num + 1, r - dropin, offset))},{str(dropin + sliceToY(num + 1, r - dropin, offset))} z" style="{style}"  />'

        # symbols
        offset = offset + 15
        # check transit
        if self.chart_type == "Transit" or self.chart_type == "Synastry":
            dropin = 54
        else:
            dropin =self.c1 -30
        symbol_x = dropin + sliceToX(num, r - dropin, offset)
        symbol_y = dropin + sliceToY(num, r - dropin, offset)
        angle_to_center = math.atan2(r - symbol_y, r - symbol_x)
        angle_degrees = math.degrees(angle_to_center)
        angle_degrees-= 90
        if 90 <= angle_degrees < 270:
            angle_degrees += 180
        rotation_transform = f'rotate({angle_degrees} {symbol_x} {symbol_y})'


        sign = f'<g transform=" {rotation_transform} translate({symbol_x}, {symbol_y}) scale(0.6) translate(-16, -16)"><use xlink:href="#{type}" /></g>'

        return slice + sign

    def _makeZodiac(self, r):
        output = ""
        for i in range(len(self.zodiac)):
            output = (
                output
                + self._zodiacSlice(
                    i,
                    r,
                    f'fill: {self.chart_colors_settings[f"zodiac_bg_{i}"]}; fill-opacity: 0;',
                    self.zodiac[i]["name"],
                )
            )
        return output
    
    def _makeHouses(self, r):
        path = ""
        xr = 12

        for i in range(xr):
            # check transit
            if self.chart_type == "Transit" or self.chart_type == "Synastry":
                dropin = 160
                roff = 72
                t_roff = 36
            else:
                dropin = self.c1 
                roff = self.c1 

            # offset is negative desc houses_degree_ut[6]
            offset = (int(self.user.houses_degree_ut[int(xr / 2)]) / -1) + int(self.user.houses_degree_ut[i])
            x1 = sliceToX(0, (r - dropin), offset) + dropin
            y1 = sliceToY(0, (r - dropin), offset) + dropin
            x2 = sliceToX(0, r - roff, offset) + roff
            y2 = sliceToY(0, r - roff, offset) + roff

            if i < (xr - 1):
                text_offset = offset + int(degreeDiff(self.user.houses_degree_ut[(i + 1)], self.user.houses_degree_ut[i]) / 2)
            else:
                text_offset = offset + int(degreeDiff(self.user.houses_degree_ut[0], self.user.houses_degree_ut[(xr - 1)]) / 2)

            # mc, asc, dsc, ic
            if i == 0:
                linecolor = self.planets_settings[12]["color"]
            elif i == 9:
                linecolor = self.planets_settings[13]["color"]
            elif i == 6:
                linecolor = self.planets_settings[14]["color"]
            elif i == 3:
                linecolor = self.planets_settings[15]["color"]
            else:
                linecolor = self.chart_colors_settings["houses_radix_line"]

            # Transit houses lines.
            if self.chart_type == "Transit" or self.chart_type == "Synastry":
                # Degrees for point zero.

                zeropoint = 360 - self.user.houses_degree_ut[6]
                t_offset = zeropoint + self.t_user.houses_degree_ut[i]
                if t_offset > 360:
                    t_offset = t_offset - 360
                t_x1 = sliceToX(0, (r - t_roff), t_offset) + t_roff
                t_y1 = sliceToY(0, (r - t_roff), t_offset) + t_roff
                t_x2 = sliceToX(0, r, t_offset)
                t_y2 = sliceToY(0, r, t_offset)
                if i < 11:
                    t_text_offset = t_offset + int(degreeDiff(self.t_user.houses_degree_ut[(i + 1)], self.t_user.houses_degree_ut[i]) / 2)
                else:
                    t_text_offset = t_offset + int(degreeDiff(self.t_user.houses_degree_ut[0], self.t_user.houses_degree_ut[11]) / 2)
                # linecolor
                if i == 0 or i == 9 or i == 6 or i == 3:
                    t_linecolor = linecolor
                else:
                    t_linecolor = self.chart_colors_settings["houses_transit_line"]
                xtext = sliceToX(0, (r - 8), t_text_offset) + 8
                ytext = sliceToY(0, (r - 8), t_text_offset) + 8

                if self.chart_type == "Transit":
                    path = path + '<text style="fill: #00f; fill-opacity: 0; font-size: 14px"><tspan x="' + str(xtext - 3) + '" y="' + str(ytext + 3) + '">' + str(i + 1) + "</tspan></text>"
                    path = f"{path}<line x1='{str(t_x1)}' y1='{str(t_y1)}' x2='{str(t_x2)}' y2='{str(t_y2)}' style='stroke: {t_linecolor}; stroke-width: 2px; stroke-opacity:1;'/>"

                else:
                    path = path + '<text style="fill: #0f0; fill-opacity: .4; font-size: 14px"><tspan x="' + str(xtext - 3) + '" y="' + str(ytext + 3) + '">' + str(i + 1) + "</tspan></text>"
                    path = f"{path}<line x1='{str(t_x1)}' y1='{str(t_y1)}' x2='{str(t_x2)}' y2='{str(t_y2)}' style='stroke: {t_linecolor}; stroke-width: 2px; stroke-opacity:1;'/>"

            # if transit
            if self.chart_type == "Transit" or self.chart_type == "Synastry":
                dropin = self.c1 + 10
            elif self.chart_type == "ExternalNatal" or self.chart_type == "Natal":
                dropin = self.c1 + 17
                
            compensation = 1
            xtext = sliceToX(0, (r - (dropin + compensation )), text_offset) + dropin  + compensation
            ytext = sliceToY(0, (r - (dropin + compensation )), text_offset) + dropin  + compensation
            
            xhouse = sliceToX(0, (r - dropin), text_offset) + dropin  
            yhouse = sliceToY(0, (r - dropin), text_offset) + dropin  
            
            angle_to_center = math.atan2(r - ytext , r - xtext)
            angle_degrees = math.degrees(angle_to_center)
            angle_degrees -= 90
            if 90 <= angle_degrees < 270:
                angle_degrees += 180
            

            path = f'{path}<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="stroke: {linecolor}; stroke-width: 2px; stroke-dasharray:3,2; stroke-opacity:1;"/>'
            path = path + f'<circle cx="{xhouse}" cy="{yhouse}" r="6" fill="#fff" opacity="1"/>'
            path = path + f'<text  transform="rotate({angle_degrees} {xtext} {ytext})" style="fill:{self.chart_colors_settings["paper_1"]}; fill-opacity: 1; font-size: 8px" x="{xtext}" y="{ytext}" dominant-baseline="middle" text-anchor="middle">{i + 1}</text>'

        return path

    def _value_element_from_planet(self, i):
        """
        Calculate chart element points from a planet.
        """

        # element: get extra points if planet is in own zodiac sign.
        related_zodiac_signs = self.available_planets_setting[i]["related_zodiac_signs"]
        cz = self.points_sign[i]
        extra_points = 0
        if related_zodiac_signs != []:
            for e in range(len(related_zodiac_signs)):
                if int(related_zodiac_signs[e]) == int(cz):
                    extra_points = self.planet_in_zodiac_extra_points

        ele = self.zodiac[self.points_sign[i]]["element"]
        if ele == "fire":
            self.fire = self.fire + self.available_planets_setting[i]["element_points"] + extra_points

        elif ele == "earth":
            self.earth = self.earth + self.available_planets_setting[i]["element_points"] + extra_points

        elif ele == "air":
            self.air = self.air + self.available_planets_setting[i]["element_points"] + extra_points

        elif ele == "water":
            self.water = self.water + self.available_planets_setting[i]["element_points"] + extra_points

    def _make_planets(self, r):
        planets_degut = {}
        def _value_element_from_planet(self, i):
            pass

        for i in range(len(self.available_planets_setting)):
            if self.available_planets_setting[i]["is_active"] == 1:
                logging.debug(f"planet: {i}, degree: {self.points_deg_ut[i]}")
                planets_degut[self.points_deg_ut[i]] = i

            self._value_element_from_planet(i)

        keys = list(planets_degut.keys())
        keys.sort()

        planets = [(planets_degut[key], key) for key in keys]

        def adjust_planet_angles(planets):
            planets.sort(key=lambda planet: planet[1])
            n = len(planets)
            adjusted_angles = [planets[0][1]]
            
            detection_distance = 5
            new_distance = 6.5
            
            for i in range(1, n):
                previous_angle = adjusted_angles[-1]
                current_angle = planets[i][1]

                if current_angle - previous_angle < detection_distance:
                    current_angle = previous_angle + new_distance

                adjusted_angles.append(current_angle)

            for i in range(n):
                for j in range(i + 1, n):
                    if abs(adjusted_angles[j] - adjusted_angles[i]) < detection_distance:
                        adjusted_angles[j] = (adjusted_angles[i] + new_distance) % 360

            for i in range(n):
                planets[i] = (planets[i][0], adjusted_angles[i])

            return planets

        adjusted_planets = adjust_planet_angles(planets)
        
        output = ""
        scale = 0.6
        rplanet = 101
        
        for planet in adjusted_planets:
            i, adjusted_angle = planet
            offset = adjusted_angle + (int(self.user.houses_degree_ut[6]) / -1)
            planet_x = sliceToX(0, (r - rplanet), offset) + rplanet
            planet_y = sliceToY(0, (r - rplanet), offset) + rplanet

            output += f'<g transform="translate(-{12 * scale},-{12 * scale})"><g transform="scale({scale})"><use x="{planet_x * (1/scale)}" y="{planet_y * (1/scale)}" xlink:href="#{self.available_planets_setting[i]["name"]}" /></g></g>'

            trueoffset = (int(self.user.houses_degree_ut[6]) / -1) + int(self.points_deg_ut[i])
            # line1
            linelenght = 12.5
            x1 = sliceToX(0, (r - self.c3), trueoffset) + self.c3
            y1 = sliceToY(0, (r - self.c3), trueoffset) + self.c3
            x2 = sliceToX(0, (r - rplanet - linelenght), trueoffset) + rplanet + linelenght
            y2 = sliceToY(0, (r - rplanet - linelenght), trueoffset) + rplanet + linelenght
            color = "white"
            output += (
                '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke-width:1px;stroke:%s;stroke-opacity:1;"/>\n'
                % (x1, y1, x2, y2, color)
            )

        return output

    def _makePatterns(self):
        """
        * Stellium: At least four planets linked together in a series of continuous conjunctions.
        * Grand trine: Three trine aspects together.
        * Grand cross: Two pairs of opposing planets squared to each other.
        * T-Square: Two planets in opposition squared to a third.
        * Yod: Two qunicunxes together joined by a sextile.
        """
        conj = {}  # 0
        opp = {}  # 10
        sq = {}  # 5
        tr = {}  # 6
        qc = {}  # 9
        sext = {}  # 3
        for i in range(len(self.available_planets_setting)):
            a = self.points_deg_ut[i]
            qc[i] = {}
            sext[i] = {}
            opp[i] = {}
            sq[i] = {}
            tr[i] = {}
            conj[i] = {}
            # skip some points
            n = self.available_planets_setting[i]["name"]
            if n == "earth" or n == "True_Node" or n == "osc. apogee" or n == "intp. apogee" or n == "intp. perigee":
                continue
            if n == "Dsc" or n == "Ic":
                continue
            for j in range(len(self.available_planets_setting)):
                # skip some points
                n = self.available_planets_setting[j]["name"]
                if n == "earth" or n == "True_Node" or n == "osc. apogee" or n == "intp. apogee" or n == "intp. perigee":
                    continue
                if n == "Dsc" or n == "Ic":
                    continue
                b = self.points_deg_ut[j]
                delta = float(degreeDiff(a, b))
                # check for opposition
                xa = float(self.aspects_settings[10]["degree"]) - float(self.aspects_settings[10]["orb"])
                xb = float(self.aspects_settings[10]["degree"]) + float(self.aspects_settings[10]["orb"])
                if xa <= delta <= xb:
                    opp[i][j] = True
                # check for conjunction
                xa = float(self.aspects_settings[0]["degree"]) - float(self.aspects_settings[0]["orb"])
                xb = float(self.aspects_settings[0]["degree"]) + float(self.aspects_settings[0]["orb"])
                if xa <= delta <= xb:
                    conj[i][j] = True
                # check for squares
                xa = float(self.aspects_settings[5]["degree"]) - float(self.aspects_settings[5]["orb"])
                xb = float(self.aspects_settings[5]["degree"]) + float(self.aspects_settings[5]["orb"])
                if xa <= delta <= xb:
                    sq[i][j] = True
                # check for qunicunxes
                xa = float(self.aspects_settings[9]["degree"]) - float(self.aspects_settings[9]["orb"])
                xb = float(self.aspects_settings[9]["degree"]) + float(self.aspects_settings[9]["orb"])
                if xa <= delta <= xb:
                    qc[i][j] = True
                # check for sextiles
                xa = float(self.aspects_settings[3]["degree"]) - float(self.aspects_settings[3]["orb"])
                xb = float(self.aspects_settings[3]["degree"]) + float(self.aspects_settings[3]["orb"])
                if xa <= delta <= xb:
                    sext[i][j] = True

        yot = {}
        # check for double qunicunxes
        for k, v in qc.items():
            if len(qc[k]) >= 2:
                # check for sextile
                for l, w in qc[k].items():
                    for m, x in qc[k].items():
                        if m in sext[l]:
                            if l > m:
                                yot["%s,%s,%s" % (k, m, l)] = [k, m, l]
                            else:
                                yot["%s,%s,%s" % (k, l, m)] = [k, l, m]
        tsquare = {}
        # check for opposition
        for k, v in opp.items():
            if len(opp[k]) >= 1:
                # check for square
                for l, w in opp[k].items():
                    for a, b in sq.items():
                        if k in sq[a] and l in sq[a]:
                            logging.debug(f"Got tsquare {a} {k} {l}")
                            if k > l:
                                tsquare[f"{a},{l},{k}"] = f"{self.available_planets_setting[a]['label']} => {self.available_planets_setting[l]['label']}, {self.available_planets_setting[k]['label']}"

                            else:
                                tsquare[f"{a},{k},{l}"] = f"{self.available_planets_setting[a]['label']} => {self.available_planets_setting[k]['label']}, {self.available_planets_setting[l]['label']}"

        stellium = {}
        # check for 4 continuous conjunctions
        for k, v in conj.items():
            if len(conj[k]) >= 1:
                # first conjunction
                for l, m in conj[k].items():
                    if len(conj[l]) >= 1:
                        for n, o in conj[l].items():
                            # skip 1st conj
                            if n == k:
                                continue
                            if len(conj[n]) >= 1:
                                # third conjunction
                                for p, q in conj[n].items():
                                    # skip first and second conj
                                    if p == k or p == n:
                                        continue
                                    if len(conj[p]) >= 1:
                                        # fourth conjunction
                                        for r, s in conj[p].items():
                                            # skip conj 1,2,3
                                            if r == k or r == n or r == p:
                                                continue

                                            l = [k, n, p, r]
                                            l.sort()
                                            stellium["%s %s %s %s" % (l[0], l[1], l[2], l[3])] = "%s %s %s %s" % (
                                                self.available_planets_setting[l[0]]["label"],
                                                self.available_planets_setting[l[1]]["label"],
                                                self.available_planets_setting[l[2]]["label"],
                                                self.available_planets_setting[l[3]]["label"],
                                            )
        out = '<g transform="translate(-30,380)">'
        if len(yot) >= 1:
            y = 0
            for k, v in yot.items():
                out += f'<text y="{y}" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 12px;">{"Yot"}</text>'

                # first planet symbol
                out += f'<g transform="translate(20,{y})">'
                out += f'<use transform="scale(0.4)" x="0" y="-20" xlink:href="#{self.available_planets_setting[yot[k][0]]["name"]}" /></g>'

                # second planet symbol
                out += f'<g transform="translate(30,{y})">'
                out += f'<use transform="scale(0.4)" x="0" y="-20" xlink:href="#{self.available_planets_setting[yot[k][1]]["name"]}" /></g>'

                # third planet symbol
                out += f'<g transform="translate(40,{y})">'
                out += f'<use transform="scale(0.4)" x="0" y="-20" xlink:href="#{self.available_planets_setting[yot[k][2]]["name"]}" /></g>'

                y = y + 14
        # finalize
        out += "</g>"
        # return out
        return ""

    # Aspect and aspect grid functions for natal type charts.
    def _makeAspects(self, r, ar):
        out = ""
        for element in self.aspects_list:
            out += self._drawAspect(
                r,
                ar-3.6, 
                element["p1_abs_pos"],
                element["p2_abs_pos"],
                self.aspects_settings[element["aid"]]["color"],
            )

        return out

    def _makeAspectGrid(self, r):
        out = ""
        style = "stroke:%s; stroke-width: 1px; stroke-opacity:.6; fill:none" % (self.chart_colors_settings["paper_0"])
        xindent = 380 
        yindent = 750 
        box = 14
        revr = list(range(len(self.available_planets_setting)))
        revr.reverse()
        counter = 0
        
        aspect_coordinates = {
            0: {"x": 1, "y": -1},
            30: {"x": 0, "y": 0}, 
            45: {"x": 0, "y": 0}, 
            60: {"x": 1.2, "y": -0.5},
            72: {"x": 0.5, "y": -1.5},
            90: {"x": 0.5, "y": -1},
            120: {"x": 0.8, "y": -1},
            135: {"x": 0, "y": 0},
            144: {"x": 0, "y": 0},
            150: {"x": 0, "y": 0},
            180: {"x": 0, "y": -2},
        }
        
        for a in revr:
            counter += 1
            if self.available_planets_setting[a]["is_active"] == 1:
                out += f'<rect x="{xindent}" y="{yindent}" width="{box}" height="{box}" style="{style}"/>'
                out += f'<use transform="scale(0.4)" x="{(xindent+2)*2.5}" y="{(yindent+1)*2.5}" xlink:href="#{self.available_planets_setting[a]["name"]}" />'

                xindent = xindent + box
                yindent = yindent - box
                revr2 = list(range(a))
                revr2.reverse()
                xorb = xindent
                yorb = yindent + box
                for b in revr2:
                    if self.available_planets_setting[b]["is_active"] == 1:
                        out += f'<rect x="{xorb}" y="{yorb}" width="{box}" height="{box}" style="{style}"/>'

                        xorb = xorb + box
                        for element in self.aspects_list:
                            if (element["p1"] == a and element["p2"] == b) or (element["p1"] == b and element["p2"] == a):
                                aspect_degrees = element["aspect_degrees"]
                                if aspect_degrees in aspect_coordinates:
                                    x_correction = aspect_coordinates[aspect_degrees]["x"]
                                    y_correction = aspect_coordinates[aspect_degrees]["y"]
                                    out += f'<use x="{xorb - box + 1 + x_correction}" y="{yorb + 3 + y_correction}" xlink:href="#orb{aspect_degrees}" />'
                                

        return out

    # Aspect and aspect grid functions for transit type charts
    def _makeAspectsTransit(self, r, ar):
        out = ""

        self.aspects_list = SynastryAspects(self.user, self.t_user, new_settings_file=self.new_settings_file).relevant_aspects

        for element in self.aspects_list:
            out += self._drawAspect(
                r,
                ar,
                element["p1_abs_pos"],
                element["p2_abs_pos"],
                self.aspects_settings[element["aid"]]["color"],
            )

        return out

    def _makeAspectTransitGrid(self, r):
        out = '<g transform="translate(500,310)">'
        out += f'<text y="-15" x="0" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 14px;">{self.language_settings["aspects"]}:</text>'

        line = 0
        nl = 0

        for i in range(len(self.aspects_list)):
            if i == 12:
                nl = 100
                
                line = 0

            elif i == 24:
                nl = 200

                line = 0

            elif i == 36:
                nl = 300
                
                line = 0
                    
            elif i == 48:
                nl = 400

                # When there are more than 60 aspects, the text is moved up
                if len(self.aspects_list) > 60:
                    line = -1 * (len(self.aspects_list) - 60) * 14
                else:
                    line = 0

            out += f'<g transform="translate({nl},{line})">'
            
            # first planet symbol
            out += f'<use transform="scale(0.4)" x="0" y="3" xlink:href="#{self.planets_settings[self.aspects_list[i]["p1"]]["name"]}" />'
            
            # aspect symbol
            out += f'<use  x="15" y="0" xlink:href="#orb{self.aspects_settings[self.aspects_list[i]["aid"]]["degree"]}" />'
            
            # second planet symbol
            out += '<g transform="translate(30,0)">'
            out += '<use transform="scale(0.4)" x="0" y="3" xlink:href="#%s" />' % (self.planets_settings[self.aspects_list[i]["p2"]]["name"]) 
            
            out += "</g>"
            # difference in degrees
            out += f'<text y="8" x="45" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 10px;">{self._dec2deg(self.aspects_list[i]["orbit"])}</text>'
            # line
            out += "</g>"
            line = line + 14
        out += "</g>"
        return out

    def _makeElements(self, r):
        total = self.fire + self.earth + self.air + self.water
        pf = int(round(100 * self.fire / total))
        pe = int(round(100 * self.earth / total))
        pa = int(round(100 * self.air / total))
        pw = int(round(100 * self.water / total))

        out = '<g transform="translate(-30,79)">'
        out += f'<text y="0" style="fill:#ff6600; font-size: 10px;">{self.language_settings["fire"]}  {str(pf)}%</text>'
        out += f'<text y="12" style="fill:#6a2d04; font-size: 10px;">{self.language_settings["earth"]} {str(pe)}%</text>'
        out += f'<text y="24" style="fill:#6f76d1; font-size: 10px;">{self.language_settings["air"]}   {str(pa)}%</text>'
        out += f'<text y="36" style="fill:#630e73; font-size: 10px;">{self.language_settings["water"]} {str(pw)}%</text>'
        out += "</g>"

        return out

    def _makePlanetGrid(self):
        li = 10
        offset = 0

        out = '<g transform="translate(50,550)">' 
        out += '<g transform="translate(80, -15)">' 
        out += "</g>"

        end_of_line = None
        for i in range(len(self.available_planets_setting)):
            offset_between_lines = 14
            end_of_line = "</g>"

            if i == 27:
                li = 10
                offset = -120

            # start of line
            out += f'<g transform="translate({offset},{li})">'

            # planet text
            out += f'<text text-anchor="start" x="-20" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 10px;">{self.language_settings["celestial_points"][self.available_planets_setting[i]["label"]]}</text>'

            # planet degree
            out += f'<text text-anchor="start" x="35" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 10px;">{self._dec2deg(self.points_deg[i])}</text>'

            # planet retrograde
            if self.points_retrograde[i]:
                out += '<g transform="translate(80,-6)"><use transform="scale(.5)" xlink:href="#retrograde" /></g>'

            # end of line
            out += end_of_line

            li = li + offset_between_lines

        if self.chart_type == "Transit" or self.chart_type == "Synastry":
            if self.chart_type == "Transit":
                out += '<g transform="translate(320, -15)">'
                out += f'<text text-anchor="start" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 14px;">{self.t_name}:</text>'
            else:
                out += '<g transform="translate(380, -15)">'
                out += f'<text text-anchor="start" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 14px;">{self.language_settings["planets_and_house"]} {self.t_user.name}:</text>'

            out += end_of_line

            t_li = 10
            t_offset = 250

            for i in range(len(self.available_planets_setting)):
                if i == 27:
                    t_li = 10
                    t_offset = -120

                if self.available_planets_setting[i]["is_active"] == 1:
                    # start of line
                    out += f'<g transform="translate({t_offset},{t_li})">'

                    # planet text
                    out += f'<text text-anchor="start" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 10px;">{self.language_settings["celestial_points"][self.available_planets_setting[i]["label"]]}</text>'
                    # planet symbol
                    out += f'<g transform="translate(5,-8)"><use transform="scale(0.4)" xlink:href="#{self.available_planets_setting[i]["name"]}" /></g>'
                    # planet degree
                    out += f'<text text-anchor="start" x="19" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 10px;">{self._dec2deg(self.t_points_deg[i])}</text>'
                    # zodiac
                    out += f'<g transform="translate(60,-8)"><use transform="scale(0.3)" xlink:href="#{self.zodiac[self.t_points_sign[i]]["name"]}" /></g>'

                    # planet retrograde
                    if self.t_points_retrograde[i]:
                        out += '<g transform="translate(74,-6)"><use transform="scale(.5)" xlink:href="#retrograde" /></g>'

                    # end of line
                    out += end_of_line

                    t_li = t_li + offset_between_lines

        if end_of_line is None:
            raise KerykeionException("End of line not found")

        out += end_of_line
        return out

    def _makeHousesGrid(self):
        out = '<g transform="translate(600,-20)">'

        li = 10
        for i in range(12):
            if i < 9:
                cusp = "&#160;&#160;" + str(i + 1)
            else:
                cusp = str(i + 1)
            out += f'<g transform="translate(0,{li})">'
            out += f'<text text-anchor="end" x="40" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 10px;">{self.language_settings["cusp"]} {cusp}:</text>'
            out += f'<g transform="translate(40,-8)"><use transform="scale(0.3)" xlink:href="#{self.zodiac[self.houses_sign_graph[i]]["name"]}" /></g>'
            out += f'<text x="53" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 10px;"> {self._dec2deg(self.user.houses_list[i]["position"])}</text>'
            out += "</g>"
            li = li + 14

        out += "</g>"

        if self.chart_type == "Synastry":
            out += '<g transform="translate(840, -20)">'
            li = 10
            for i in range(12):
                if i < 9:
                    cusp = "&#160;&#160;" + str(i + 1)
                else:
                    cusp = str(i + 1)
                out += '<g transform="translate(0,' + str(li) + ')">'
                out += f'<text text-anchor="end" x="40" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 10px;">{self.language_settings["cusp"]} {cusp}:</text>'
                out += f'<g transform="translate(40,-8)"><use transform="scale(0.3)" xlink:href="#{self.zodiac[self.t_houses_sign_graph[i]]["name"]}" /></g>'
                out += f'<text x="53" style="fill:{self.chart_colors_settings["paper_0"]}; font-size: 10px;"> {self._dec2deg(self.t_user.houses_list[i]["position"])}</text>'
                out += "</g>"
                li = li + 14
            out += "</g>"

        return out

    def _createTemplateDictionary(self) -> ChartTemplateDictionary:
        # empty element points
        self.fire = 0.0
        self.earth = 0.0
        self.air = 0.0
        self.water = 0.0

        # width and height from screen
        ratio = float(self.screen_width) / float(self.screen_height)
        if ratio < 1.3: 
            wm_off = 130
        else:  
            wm_off = 100

        # Viewbox and sizing
        svgHeight = "100%"
        svgWidth = "100%"
        rotate = "0"
        translate = "0"
        
        # To increase the size of the chart, change the viewbox
        if self.chart_type == "Natal" or self.chart_type == "ExternalNatal":
            viewbox = self.chart_settings["basic_chart_viewBox"]
        else:
            viewbox = self.chart_settings["wide_chart_viewBox"]

        # template dictionary
        td: ChartTemplateDictionary = dict() 
        r = 240

        if self.chart_type == "ExternalNatal" or self.chart_type == "Natal":
            self.c1 = 56
            self.c2 = 92
            self.c3 = 110
        else:
            self.c1 = 12
            self.c2 = 36
            self.c3 = 72

        # transit
        if self.chart_type == "Transit" or self.chart_type == "Synastry":
            td["font"] = self.font
            td["transitRing"] = self._transitRing(r)
            td["degreeRing"] = self._degreeTransitRing(r)

            # circles
            td["c1"] = f'cx="{r}" cy="{r}" r="{r - 36}"'
            td["c1style"] = f'fill: none; stroke: {self.chart_colors_settings["zodiac_transit_ring_2"]}; stroke-width: 1px; stroke-opacity:.4;'




            td["c3"] = 'cx="' + str(r) + '" cy="' + str(r) + '" r="' + str(r - 160) + '"'
            if self.bg_image_wheel_is_active == True:
                td["bg_image_wheel"] = self.bg_image_wheel_pattern
                td["c3style"] = f'fill:url(#image); fill-opacity:1; stroke: {self.chart_colors_settings["zodiac_radix_ring_0"]}; stroke-width: 1px'
            else:
                td["bg_image_wheel"] = self.bg_image_wheel_pattern
                td["c3style"] = f"fill: {self.chart_colors_settings['paper_1']}; fill-opacity:1; stroke: {self.chart_colors_settings['zodiac_transit_ring_0']}; stroke-width: 1px"
            td["makeAspects"] = self._makeAspectsTransit(r, (r - 160))
            td["makeAspectGrid"] = self._makeAspectTransitGrid(r)
            td["makePatterns"] = ""
            td["chart_width"] = self.full_width
        else:
            td["font"] = self.font
            td["font_name"] = self.font_name
            td["transitRing"] = ""
            td["degreeRing"] = self._degreeRing(r)


            self.offset = 360 - self.user.houses_degree_ut[6]
            perimeter = 2 * 3.1416 * 194
            segments_number = 12
            separation_percentage = 5 
            segment_length = perimeter / segments_number 
            separation_length = segment_length * separation_percentage / 100
            separation_var = 1 

            segment_length = segment_length - separation_var * separation_length
            separation_length = separation_length * separation_var

            dasharray = f"{segment_length} {separation_length}"
            td["c1"] = f'cx="{r}" cy="{r}" r="{r - 46}"'
            td["c1style"] = f'fill: none; stroke: {self.chart_colors_settings["zodiac_radix_ring_2"]}; stroke-width: 3px; stroke-dasharray: {dasharray}; stroke-dashoffset: {(perimeter/360*self.offset)-5}'
            td["c2"] = f'cx="{r}" cy="{r}" r="{r - self.c2}"'
            td["c2style"] = f'fill: {self.chart_colors_settings["paper_1"]}; fill-opacity:0; stroke: {self.chart_colors_settings["zodiac_radix_ring_1"]}; stroke-opacity:.4; stroke-width: 1px'
            td["c3"] = f'cx="{r}" cy="{r}" r="{r - self.c3}"'
            if self.bg_image_wheel_is_active == True:
                td["bg_image_wheel"] = self.bg_image_wheel_pattern
                td["c3style"] = f'fill:url(#image); fill-opacity:1; stroke: {self.chart_colors_settings["zodiac_radix_ring_0"]}; stroke-width: 1px'
            else:
                td["bg_image_wheel"] = self.bg_image_wheel_pattern
                td["c3style"] = f'fill: {self.chart_colors_settings["paper_1"]}; fill-opacity:1; stroke: {self.chart_colors_settings["zodiac_radix_ring_0"]}; stroke-width: 1px'
            td["makeAspects"] = self._makeAspects(r, (r - self.c3))
            td["makeAspectGrid"] = self._makeAspectGrid(r)
            td["makePatterns"] = self._makePatterns()
            td["chart_width"] = self.natal_width

        td["circleX"] = str(0)
        td["circleY"] = str(0)
        td["svgWidth"] = str(svgWidth)
        td["svgHeight"] = str(svgHeight)
        td["viewbox"] = viewbox


        if self.chart_type == "Synastry":
            td["stringTitle"] = f"{self.name} {self.language_settings['and_word']} {self.t_user.name}"

        elif self.chart_type == "Transit":
            td["stringTitle"] = f"{self.language_settings['transits']} {self.t_user.day}/{self.t_user.month}/{self.t_user.year}"

        else:
            td["stringTitle"] = self.name

        if self.chart_type == "Synastry" or self.name == "Transit":
            td["stringName"] = ""
        else:
            td["stringName"] = ""




        if self.name_spacing:
            ystringDateTime = 90
        else:
            ystringDateTime= 80

        ystringLocation = ystringDateTime + 20
        ystringLat= ystringLocation +20
        ystringLon =  ystringLat +20 

        td["ystringDateTime"] = ystringDateTime
        td["ystringLat"] = ystringLat
        td["ystringLon"] = ystringLon
        td["ystringLocation"] = ystringLocation
        
        # bottom left
        td["bottomLeft1"] = ""
        td["bottomLeft2"] = ""
        td["bottomLeft3"] = ""
        td["bottomLeft4"] = ""

        # lunar phase
        deg = self.user.lunar_phase["degrees_between_s_m"]

        lffg = None
        lfbg = None
        lfcx = None
        lfr = None

        if deg < 90.0:
            maxr = deg
            if deg > 80.0:
                maxr = maxr * maxr
            lfcx = 20.0 + (deg / 90.0) * (maxr + 10.0)
            lfr = 10.0 + (deg / 90.0) * maxr
            lffg = self.chart_colors_settings["lunar_phase_0"]
            lfbg = self.chart_colors_settings["lunar_phase_1"]

        elif deg < 180.0:
            maxr = 180.0 - deg
            if deg < 100.0:
                maxr = maxr * maxr
            lfcx = 20.0 + ((deg - 90.0) / 90.0 * (maxr + 10.0)) - (maxr + 10.0)
            lfr = 10.0 + maxr - ((deg - 90.0) / 90.0 * maxr)
            lffg = self.chart_colors_settings["lunar_phase_1"]
            lfbg = self.chart_colors_settings["lunar_phase_0"]

        elif deg < 270.0:
            maxr = deg - 180.0
            if deg > 260.0:
                maxr = maxr * maxr
            lfcx = 20.0 + ((deg - 180.0) / 90.0 * (maxr + 10.0))
            lfr = 10.0 + ((deg - 180.0) / 90.0 * maxr)
            lffg, lfbg = self.chart_colors_settings["lunar_phase_1"], self.chart_colors_settings["lunar_phase_0"]

        elif deg < 361:
            maxr = 360.0 - deg
            if deg < 280.0:
                maxr = maxr * maxr
            lfcx = 20.0 + ((deg - 270.0) / 90.0 * (maxr + 10.0)) - (maxr + 10.0)
            lfr = 10.0 + maxr - ((deg - 270.0) / 90.0 * maxr)
            lffg, lfbg = self.chart_colors_settings["lunar_phase_0"], self.chart_colors_settings["lunar_phase_1"]

        if lffg is None or lfbg is None or lfcx is None or lfr is None:
            raise KerykeionException("Lunar phase error")

        td["lunar_phase_fg"] = ""
        td["lunar_phase_bg"] = "#1d2c56"
        td["lunar_phase_cx"] = ""
        td["lunar_phase_r"] = ""
        td["lunar_phase_outline"] = ""

        td["lunar_phase_rotate"] = ""

        # stringlocation
        if len(self.location) > 35:
            split = self.location.split(",")
            if len(split) > 1:
                td["stringLocation"] = split[0] + ", " + split[-1]
                if len(td["stringLocation"]) > 35:
                    td["stringLocation"] = td["stringLocation"][:35] + "..."
            else:
                td["stringLocation"] = self.location[:35] + "..."
        else:
            td["stringLocation"] = self.location

        td["stringDateTime"] = f"{self.user.day} {self.user.month_name} {self.user.year} · {self.user.hour:02d}:{self.user.minute:02d}"

        if self.chart_type == "Synastry":
            td["stringLat"] = f"{self.t_user.name}: "
            td["stringLon"] = self.t_user.city
            td["stringPosition"] = f"{self.t_user.day} {self.t_user.month} {self.t_user.year} {self.t_user.hour:02d}:{self.t_user.minute:02d}"

        else:
            td["stringLat"] = f"{self._lat2str(self.geolat)}"
            td["stringLon"] = f"{self._lon2str(self.geolon)}"
            td["stringPosition"] = f"{self.language_settings['type']}: {self.charttype}"

        # paper_color_X
        td["paper_color_0"] = self.chart_colors_settings["paper_0"]
        if self.bg_color is not None:
            td["paper_color_1"] = self.bg_color
        else:
            td["paper_color_1"] = self.chart_colors_settings["paper_1"]

        #background
        td["bg_image"] = self.bg_image
        
        # planets_color_X
        for i in range(len(self.planets_settings)):
            planet_id = self.planets_settings[i]["id"]
            td[f"planets_color_{planet_id}"] = self.planets_settings[i]["color"]

        # zodiac_color_X
        for i in range(12):
            td[f"zodiac_color_{i}"] = self.chart_colors_settings[f"zodiac_icon_{i}"]

        # orb_color_X
        for i in range(len(self.aspects_settings)):
            td[f"orb_color_{self.aspects_settings[i]['degree']}"] = self.aspects_settings[i]['color']

        # config
        td["cfgZoom"] = str(self.zoom)
        td["cfgRotate"] = rotate
        td["cfgTranslate"] = translate

        # functions
        td["makeZodiac"] = self._makeZodiac(r)
        td["makeHouses"] = self._makeHouses(r)
        td["makePlanets"] = self._make_planets(r)
        td["makeElements"] = self._makeElements(r)
        td["makePlanetGrid"] = self._makePlanetGrid()
        td["makeHousesGrid"] = self._makeHousesGrid()

        return td

    def makeTemplate(self):
        """Creates the template for the SVG file"""
        td = self._createTemplateDictionary()

        # read template
        with open(self.xml_svg, "r", encoding="utf-8", errors="ignore") as output_file:
            f = open(self.xml_svg)
            template = Template(f.read()).substitute(td)

        # return filename

        logging.debug(f"Template dictionary keys: {td.keys()}")

        self._createTemplateDictionary()
        return template.replace('"', "'")

    def makeSVG(self) -> None:
        """Prints out the SVG file in the specifide folder"""

        if not (self.template):
            self.template = self.makeTemplate()

        self.chartname = self.output_directory / f"{self.name}{self.chart_type}Chart.svg"

        with open(self.chartname, "w", encoding="utf-8", errors="ignore") as output_file:
            output_file.write(self.template)

        logging.info(f"SVG Generated Correctly in: {self.chartname}")


if __name__ == "__main__":
    from kerykeion.utilities import setup_logging
    #setup_logging(level="debug")

    first = AstrologicalSubject("John ", 2003, 2, 22, 3, 5, "Bogota", "CO")
    second = AstrologicalSubject("Paul McCartney", 1942, 6, 18, 15, 30, "Bogota", "CO")

    natalChart = KerykeionChartSVG(first, "Natal", None, None, None, "Symbol" , "Gadugi", "#7D4BE7" , None, None,None)
    natalChart.makeSVG()
    
    natalChart2 = KerykeionChartSVG(second, "Natal", None, None, None, "Symbol" , "Gadugi", None, None, None,None)
    natalChart2.makeSVG()
    