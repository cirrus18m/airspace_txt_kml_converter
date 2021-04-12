from matplotlib import pyplot as plt
from easygui import fileopenbox, filesavebox, msgbox
import os
import json

class Airspace_KML_converter(object):
    def __init__(self, full_path_of_source=''):
        """
        transforms airspace files from and to open air format <-> kml (google earth)
        :param full_path_of_source: path to open source file (txt or kml) - optional
        :output: writes converted file to disk
        """
        if len(full_path_of_source) == 0:
            full_path_of_source = fileopenbox(default=os.path.curdir, filetypes=["*.txt", "*.kml"])
            if full_path_of_source is None:
                print('Airspace conversion was aborted by the user')
                quit()
        # set template (this should not be changed)
        self.full_path_kml_template = r'Thermal_Map_Template5.kml' # set template file here: Folder must be named "good" and "bad"

        self.airspaces = []  # airspace container
        self.kml_template = {'header': [], 'good': [], 'bad': [], # will be filled after loading template
                             'good_subdivided': {'head':[], 'placemark': [], 'tail': []},
                             'bad_subdivided': {'head':[], 'placemark': [], 'tail': []}}
        self.txt_lines = []  # airspace file in open airspace format
        self.kml_lines = []  # airspace file in kml format
        """ handle conversion from and to KML / airspace format"""
        if full_path_of_source.lower().endswith('.kml'):
            self.kml_2_open_airspace_and_json_format(full_path_of_source)
        if full_path_of_source.lower().endswith('.txt'):
            self.open_airspace_format_2_kml(full_path_of_source)
            self.plot_all()  # works for now only for TXT input

    def kml_2_open_airspace_and_json_format(self, full_path):
        """ converts kml files to open airspace files """
        # read file
        f = open(full_path,'r')
        kml = f.readlines()
        f.close()
        # find airspaces
        """Placemark >
        < name > Bremen - Blumenthal
        Thermikplatte < / name >
        < styleUrl >  # inline10</styleUrl>
        < Polygon >
        < tessellate > 1 < / tessellate >
        < outerBoundaryIs >
        < LinearRing >
        < coordinates >
        8.529121049900063, 53.19549566929423, 0
        8.52324583919868, 53.21131939607898, 0
        8.545439298799483, 53.23055800702935, 0
        8.588991466114615, 53.23047069814625, 0
        8.575289966189502, 53.20745451706468, 0
        8.560633120477348, 53.19724609335408, 0
        8.529121049900063, 53.19549566929423, 0
            < / coordinates >
        
        < / LinearRing >
        < / outerBoundaryIs >
        < / Polygon >
        < / Placemark >"""
        container = []
        idxLine = 0
        did_not_pass_main_folder = True
        while idxLine < len(kml):
            #print(kml[idxLine])
            #if '<Folder>' in kml[idxLine] and did_not_pass_main_folder:
            #    # we have to jump over the first folder
            #    print(f'Reading everything inside folder: {kml[idxLine]}')
            #    did_not_pass_main_folder = False
            if '<Folder>' in kml[idxLine]:  # begin of airspace
                as_type = kml[idxLine+1].replace('\t','').replace('<name>','').replace('</name>\n','')  # <name>B</name>
                print('Reading AS-types: ' + as_type)
                if not (as_type == 'A' or as_type == 'B'):
                    print('#### Check Folder / Airspace Types, must be "A" or "B" and try again (current %s)' % as_type)
                    msgbox('Check Folder / Airspace Types, must be "A" or "B" and try again (current %s)' % as_type)
                    quit()

            if '<Placemark' in kml[idxLine]:  # begin of airspace
                container = []
            if '</Placemark' in kml[idxLine]:  # end of airspace
                # make sure only Polygons are stored
                for as_line in container:
                    if '<Polygon>' in as_line:
                        idx_lookAt_start = None
                        for idx, line_of_container in enumerate(container):
                            if "<LookAt>" in line_of_container:
                                idx_lookAt_start = idx
                            if "</LookAt>" in line_of_container:
                                idx_lookAt_end = idx
                        # Remove lookAt lines if necessary
                        if idx_lookAt_start:
                            container = container[0:idx_lookAt_start] + container[idx_lookAt_end+1::]  # cut out look at part
                        # append airspace to airspace list as airspace class
                        self.airspaces.append(Airspace(lines=container, file_type='kml', as_type=as_type))
            container.append(kml[idxLine])
            idxLine += 1
        print('Loaded %d airspaces from KML-file (%s)' %(len(self.airspaces),full_path))
        # summary
        outlines = ['* KML conversion file, rename this line']
        json_dict = {"circles": [], "polygons": []}
        for airspace in self.airspaces:
            # prepare open-airspace formate
            outlines.append('\n\n')  # separate airspaces
            outlines.extend(airspace.txt_lines)
            # prepare json
            json_dict['polygons'].append(airspace.json_dict)

        # write open airspace format
        target_path = full_path[:-4] + '_converted.txt'
        # uisave dialog

        target_path = filesavebox(default=target_path, filetypes="*.txt")
        if target_path is None:
            print('Airspace conversion was aborted by the user')
            quit()

        f = open(target_path,'w')
        f.writelines(outlines)
        f.close()
        print('Result was written to: %s' % target_path)

        # write json:
        target_path_json = full_path[:-4] + '_converted.json'

        json_string = json.dumps(json_dict)
        json_file = open(target_path_json, "w")
        json_file.write(json_string)
        json_file.close()


    def open_airspace_format_2_kml(self, source_file_txt):
        """
        transforms airspace in open air format to kml for google earth
        :param source_file_txt: path to open airformat
        :return:
        """
        # load template for kml file
        self.load_kml_template(self.full_path_kml_template)
        # load airspace source
        self.load_airspace_open_air_format(source_file_txt)

        self.kml_lines = self.kml_template['header']
        self.kml_lines.extend(self.kml_template['good_subdivided']['head'])
        # collect all A and B kml lines
        kml_A = []
        kml_B = []
        # transform airspaces and attach to A and B collect-lists
        for airspace in self.airspaces:
            airspace.make_kml_format(self.kml_template)
            if airspace.as_type == 'A':
                kml_A.extend(airspace.kml_lines)
            if airspace.as_type == 'B':
                kml_B.extend(airspace.kml_lines)

        self.kml_lines.extend(kml_A)
        self.kml_lines.extend(self.kml_template['good_subdivided']['tail'])
        # start B part
        self.kml_lines.extend(self.kml_template['bad_subdivided']['head'])
        self.kml_lines.extend(kml_B)
        self.kml_lines.extend(self.kml_template['bad_subdivided']['tail'])

        full_path_kml = source_file_txt[:-4] + '_converted.kml'
        # uisave dialog
        full_path_kml = filesavebox(default=full_path_kml, filetypes="*.kml")
        if full_path_kml is None:
            print('Airspace conversion was aborted by the user')
            quit()

        # write to file
        f = open(full_path_kml, 'w')
        f.writelines(self.kml_lines)
        f.close()
        print('Resulting KML files was saved to: %s' % full_path_kml)


    def load_airspace_open_air_format(self, source_file_txt):
        """
        load airspace file
        :param source_file_txt: path to open airformat
        """
        # read airspaces in open airspace format
        f = open(source_file_txt, 'r',errors='replace')
        AStxt_lines = f.readlines()
        f.close()
        # read airspaces
        container = []
        idxLine = 0
        while idxLine < len(AStxt_lines):
            if 'AC A' in AStxt_lines[idxLine]:
                #container = []
                as_type = 'A'
            if 'AC B' in AStxt_lines[idxLine]:
                #container = []
                as_type = 'B'

            if AStxt_lines[idxLine].startswith('\n'):  # empty line, usually end of airspace
                # check if this is really an airspace, could also be strePla layout, which we do not want:
                for line in container:
                    if line.startswith('AC '):
                        self.airspaces.append(Airspace(container, 'txt', as_type, self.kml_template))
                        break
                container = []
            if not AStxt_lines[idxLine].startswith('*'):
                container.append(AStxt_lines[idxLine])
            idxLine += 1

    def load_kml_template(self, full_path_kml_template):
        """ load template
        - return: dict: with
            - header
            - good (thermals)
            - bad (thermals) """
        f = open(full_path_kml_template,'r')
        kml_lines = f.readlines()
        f.close()
        # Split Files into 3 parts
        # - header
        # - TS_A: Vorlage zum speichern
        # - TS_B
        idxLine = 0
        while idxLine < len(kml_lines):
            if '<name>good_thermals</name>' in kml_lines[idxLine]:
                self.kml_template['header'] = kml_lines[:idxLine]
            if '<name>bad_thermals</name>' in kml_lines[idxLine]:
                self.kml_template['good'] = kml_lines[len(self.kml_template['header']):idxLine]
                self.kml_template['bad'] = kml_lines[idxLine:len(kml_lines)]
            idxLine += 1
        # subdivide into head, placemark and tail
        """
        <name>good_thermals</name>
			<open>1</open>
			<Placemark>
				<name>TS_Test1_A</name>
				<styleUrl>#__managed_style_012F563AF410C6D89C28</styleUrl>
				<Polygon>
					<outerBoundaryIs>
						<LinearRing>
							<coordinates>
								9.025830271397426,53.46493577242719,0 8.986157446488383,53.46952117358134,0 8.986024308034002,53.46940930378423,0 8.985302043383754,53.46903306939636,0 8.962043301887295,53.46599044595203,0 8.968576645332982,53.46168538137756,0 8.966417710231729,53.44675457151015,0 8.966524947387285,53.44638535081827,0 8.967131782344268,53.44597423810207,0 8.967793436413203,53.44537740428722,0 8.968271199353492,53.4448553774634,0 9.001090859161449,53.43746144188587,0 9.002104832473883,53.43755849249606,0 9.002921245439754,53.43773603605858,0 9.020404786676616,53.45117244097055,0 9.021175983138708,53.45155477375865,0 9.021806641340389,53.45182228413126,0 9.02243786449873,53.45209001648206,0 9.025830271397426,53.46493577242719,0 
							</coordinates>
						</LinearRing>
					</outerBoundaryIs>
				</Polygon>
			</Placemark>
		</Folder>
		<Folder>
        """
        # subdivide good thermals part
        idxLine = 0
        while idxLine < len(self.kml_template['good']):
            if '\t\t\t<Placemark>\n' in self.kml_template['good'][idxLine]:
                self.kml_template['good_subdivided']['head'] = self.kml_template['good'][:idxLine]
            if '\t\t\t</Placemark>\n' in self.kml_template['good'][idxLine]:
                self.kml_template['good_subdivided']['placemark'] = self.kml_template['good'][len(self.kml_template['good_subdivided']['head']):idxLine+1]
                # attach tail
                self.kml_template['good_subdivided']['tail'] = self.kml_template['good'][idxLine+1:]
                break
            idxLine += 1
        # subdivide bad thermals part
        idxLine = 0
        while idxLine < len(self.kml_template['bad']):
            if '\t\t\t<Placemark>\n' in self.kml_template['bad'][idxLine]:
                self.kml_template['bad_subdivided']['head'] = self.kml_template['bad'][:idxLine]
            if '\t\t\t</Placemark>\n' in self.kml_template['bad'][idxLine]:
                self.kml_template['bad_subdivided']['placemark'] = self.kml_template['bad'][len(
                    self.kml_template['good_subdivided']['head']):idxLine + 1]
                # attach tail
                self.kml_template['bad_subdivided']['tail'] = self.kml_template['bad'][idxLine + 1:]
                break
            idxLine += 1
        print('KML template was loaded from: %s' % full_path_kml_template)

    def plot_all(self):
        """
        plot all airspaces
        """
        # initialize figure
        fig = plt.figure(1)

        #ax = fig.add_subplot(1, 1, 1)
        for airspace in self.airspaces:
            airspace.plot()
        plt.show()

class Airspace(object):
    def __init__(self, lines, file_type, as_type='A', kml_template= []):
        """
        contains single airspaces
        :param lines: kml or open air format
        :param file_type: 'kml' or 'txt'
        :param asType: only relevant for kml --> then 'A' or 'B'
        :param kml_template: only relevant for kml --> template dictionary showing required format
        """
        self.name = ''
        self.as_type = as_type  # airspace type: A or B
        self.kml_lines = []
        self.txt_lines = []
        self.coordinates_kml = ''
        self.lat_dec = []  # used for plotting
        self.lon_dec = []  # used for plotting

        # import
        if file_type == 'kml':
            #print('conversion here')
            self.kml_lines = lines
            self.make_open_airspace_format()
            # generate json for maps:
            self.make_json_airspace_format()
        if file_type == 'txt':  # case open airspace format
            self.txt_lines = lines
            self.make_kml_format(kml_template)

    def make_json_airspace_format(self):
        """generates json format for web page visualization"""
        # The previous fct make_open_airspace_format already stored, coordinates_kml, name and type
        # This data is collected in an dictionary, which then is stored as json.
        # initialize  dict
        coordinates_as_list_of_floats = []
        # run through coordinates
        coordinates_as_list_of_floats = []
        for coo_pt in self.coordinates_kml.split(' ')[:-1]:
            lat_long = coo_pt.split(',')
            coordinates_as_list_of_floats.append([float(lat_long[1]), float(lat_long[0])])
        # make json dict
        self.json_dict = {"AL": "FL98", "AH": "FL99", "AC": self.as_type, "AN": self.name, "data": coordinates_as_list_of_floats}

    def make_open_airspace_format(self):
        """ convert to open airspace format"""
        # Extract coordinates from KML
        for idxline in range(len(self.kml_lines)):
            if '<name>' in self.kml_lines[idxline]:
                self.name = self.kml_lines[idxline].replace('\t', '').replace('<name>', '').replace('</name>', '').replace('\n','')
                if not self.name.startswith('TS'):
                    self.name = 'TS_' + self.name
                print('Type: %s | Name: %s' % (self.as_type, self.name))
            if '<coordinates>' in self.kml_lines[idxline]:
                self.coordinates_kml = self.kml_lines[idxline + 1].replace('\t', '').replace('\n', '')
                break
        # start conversion to airspace format
        """ AC A
            AN TS_Erzgeb
            AL FL98
            AH FL99
            DP 50:26:22 N 012:17:59 E
            DP 50:25:25 N 012:18:26 E
            DP 50:24:40 N 012:19:01 E
      DP 50:24:06 N 012:19:46 E"""

        # AC A
        self.txt_lines.append('AC %s\n' % self.as_type)
        # AN TS_Erzgeb
        self.txt_lines.append('AN %s\n' % self.name)
        # heights
        self.txt_lines.append('AL FL98\n')
        self.txt_lines.append('AH FL99\n')
        # coordinates
        for coo_pt in self.coordinates_kml.split(' ')[:-1]:
            # Target format: DP 50:26:22 N 012:17:59 E
            lat_long = coo_pt.split(',')
            # latitude
            latDecAsStr = lat_long[1].split('.')
            #if '.' not in latDecAsStr: # take care of case "51" instead of "51.123456"
            #    latDecAsStr += '.000000'
            lat_degree = abs(int(latDecAsStr[0]))
            print(f'latDecAsStr {latDecAsStr}')
            if len(latDecAsStr)==1:
                latDecAsStr.append('0')
            lat_secondDec = (float('0.' + latDecAsStr[1])*60) % 1
            lat_minute = round((float('0.' + latDecAsStr[1])*60) - lat_secondDec)
            lat_second = round(lat_secondDec*60)
            cooString = ('DP %02d:%02d:%02d' %(lat_degree,lat_minute,lat_second))
            if latDecAsStr[0].startswith('-'):
                cooString += ' S'
            else:
                cooString += ' N'
            # longitude
            print(f'converting lat_long {lat_long}')
            # take care of case: no decimal sign included, case "11" instead of "11.123456"
            if '.' not in lat_long[0]:
                lat_long[0] += '.0'
            lonDecAsStr = lat_long[0].split('.')
            lon_degree = abs(int(lonDecAsStr[0]))
            lon_secondDec = (float('0.' + lonDecAsStr[1]) * 60) % 1
            lon_minute = round((float('0.' + lonDecAsStr[1]) * 60) - lon_secondDec)
            lon_second = round(lon_secondDec * 60)
            cooString += (' %03d:%02d:%02d' % (lon_degree, lon_minute, lon_second))
            if lonDecAsStr[0].startswith('-'):
                cooString += ' W'
            else:
                cooString += ' E'
            cooString += '\n'
            self.txt_lines.append(cooString)

    def make_kml_format(self,kml_template):
        """
        uses template in order to make kml format
        :param kml_template: template lines where name and coordinates should be replaced
        :return: self.kml_lines --> definition as kml
        """
        if self.as_type == 'A':
            self.kml_lines = kml_template['good_subdivided']['placemark']
        elif self.as_type == 'B':
            self.kml_lines = kml_template['bad_subdivided']['placemark']
        else:
            print('Unknown airspace type')
        # get idx of name and coordinates
        idxLine = 0
        while idxLine < len(self.kml_lines):
            #print(self.kml_lines[idxLine]
            if self.kml_lines[idxLine].startswith('\t\t\t\t<name>'):  # begin of airspace
                idx_name = idxLine
            if '\t\t\t\t\t\t\t<coordinates>\n' in self.kml_lines[idxLine]:  # begin of airspace
                idx_coordinates = idxLine+1
            idxLine += 1
        # transform coordinates
        # add all coordinates: Format is:
        # source: 'DP 50:26:22 N 012:17:59 E\n'
        # target: 9.025830271397426,53.46493577242719,0 8.986157446488383,53.46952117358134,0
        coo_list = []  # collect list of coorinates as strings
        for line in self.txt_lines:
            if line.startswith('AN'):
                self.name = line[3:].replace('\n','')
                self.kml_lines[idx_name] = '\t\t\t\t<name>%s</name>\n' % self.name

            if line.startswith('DP'):
                # lon
                lon_deg = float(line[14:17])
                lon_min = float(line[18:20])
                lon_sec = float(line[21:23])
                lon_dec = (lon_sec / 60 + lon_min) / 60 + lon_deg
                if line[24] == 'W':
                    lon_dec *= -1  # negative if west
                # lat
                lat_deg = float(line[3:5])
                lat_min = float(line[6:8])
                lat_sec = float(line[9:11])
                lat_dec = (lat_sec / 60 + lat_min) / 60 + lat_deg
                if line[12] == 'S':
                    lat_dec *= -1  # negative if west
                # attach coordinates
                coo_list.append('%1.16f,%1.16f,0 ' % (lon_dec,lat_dec))
                # store for later plotting
                self.lat_dec.append(lat_dec)
                self.lon_dec.append(lon_dec)

        # make sure that shape is closed --> first an last point must be the same
        if coo_list[0] != coo_list[-1]:
            coo_list.append(coo_list[0])
            self.lat_dec.append(self.lat_dec[0])
            self.lon_dec.append(self.lon_dec[0])

        # write coordinate strings into kml
        self.kml_lines[idx_coordinates] = '\t\t\t\t\t\t\t\t'  # is prefix. Coordinates to be added as string below
        for pt in coo_list:
            self.kml_lines[idx_coordinates] += pt
        print('Converted airspace %s' % self.name)

    def plot(self):
        """
        Plots airspace into figure, reuse open figure if available
        :return:
        """
        # determine color
        if self.as_type=='A':
            color4plot = 'g'
        elif self.as_type == 'B':
            color4plot = 'b'
        else:
            color4plot = 'k'
        # plot
        plt.fill(self.lon_dec,self.lat_dec,facecolor=color4plot)


if __name__ == "__main__":
    print('Start of klm-converter')
    #full_path = '/home/chris/PycharmProjects/ThermalMap_GoogleEarch_connection/ConverterTest.kml'
    # full_path = '/home/chris/PycharmProjects/ThermalMap_GoogleEarch_connection/Thermal_Spaces_V219_corr.txt'

    Airspace_KML_converter(full_path_of_source='')