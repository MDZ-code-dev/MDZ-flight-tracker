// Original top-down family silhouettes, nose up, centered at (120, 120).
// Geometry stays inside a 108px radius so heading rotation cannot clip it.
const aircraftSilhouettes = {
  boeing737: {
    name: 'BOEING 737 FAMILY',
    // Broad fuselage, swept wings with underwing pods, conventional tail.
    path: 'M120 14C113 14 109 33 109 49L109 100 22 139 20 152 109 132 112 188 81 205 81 215 116 206 120 225 124 206 159 215 159 205 128 188 131 132 220 152 218 139 131 100 131 49C131 33 127 14 120 14Z M76 106C71 106 68 112 68 121L68 144 84 144 84 121C84 112 81 106 76 106Z M164 106C159 106 156 112 156 121L156 144 172 144 172 121C172 112 169 106 164 106Z'
  },
  challenger: {
    name: 'CHALLENGER 300/350 FAMILY',
    // Slender cabin, swept winglets and rear-mounted pods ahead of a T-tail.
    path: 'M120 17C116 17 113 35 113 49L113 108 24 142 22 154 113 134 115 194 87 204 87 213 117 209 120 224 123 209 153 213 153 204 125 194 127 134 218 154 216 142 127 108 127 49C127 35 124 17 120 17Z M103 157C99 157 97 163 97 169L97 187C97 191 101 194 105 194L111 194 111 166C111 160 108 157 103 157Z M137 157C132 157 129 160 129 166L129 194 135 194C139 194 143 191 143 187L143 169C143 163 141 157 137 157Z M108 173L116 173 116 180 108 180Z M124 173L132 173 132 180 124 180Z M22 142L27 135 28 149 22 154Z M218 142L213 135 212 149 218 154Z'
  },
  businessJet: {
    name: 'REAR-ENGINE BUSINESS JET',
    path: 'M120 20C116 20 114 35 114 49L114 106 28 137 27 148 114 131 116 192 84 206 84 215 117 207 120 222 123 207 156 215 156 206 124 192 126 131 213 148 212 137 126 106 126 49C126 35 124 20 120 20Z M103 156C99 156 97 161 97 168L97 187 111 190 111 166C111 160 108 156 103 156Z M137 156C132 156 129 160 129 166L129 190 143 187 143 168C143 161 141 156 137 156Z M108 172L117 172 117 179 108 179Z M123 172L132 172 132 179 123 179Z'
  },
  regionalJet: {
    name: 'REAR-ENGINE REGIONAL JET',
    path: 'M120 14C115 14 112 33 112 49L112 110 40 145 39 156 113 134 116 198 86 208 86 217 117 210 120 225 123 210 154 217 154 208 124 198 127 134 201 156 200 145 128 110 128 49C128 33 125 14 120 14Z M102 165C98 165 96 171 96 178L96 197 110 200 110 176C110 169 107 165 102 165Z M138 165C133 165 130 169 130 176L130 200 144 197 144 178C144 171 142 165 138 165Z M107 181L117 181 117 188 107 188Z M123 181L133 181 133 188 123 188Z'
  },
  triJet: {
    name: 'TRI-JET',
    // DC-10/MD-11 layout: two underwing pods and a third at the tail.
    path: 'M120 16C113 16 108 34 108 50L108 98 22 140 20 153 109 132 112 189 82 205 82 215 116 207 120 225 124 207 158 215 158 205 128 189 131 132 220 153 218 140 132 98 132 50C132 34 127 16 120 16Z M75 108C70 108 67 114 67 122L67 148 83 148 83 122C83 114 80 108 75 108Z M165 108C160 108 157 114 157 122L157 148 173 148 173 122C173 114 170 108 165 108Z M120 171C113 171 109 178 109 186L109 212 131 212 131 186C131 178 127 171 120 171Z'
  },
  rearTriJet: {
    name: 'REAR-ENGINE TRI-JET',
    // 727/Falcon layout: three engines at the rear, no underwing pods.
    path: 'M120 16C115 16 112 34 112 49L112 109 28 144 27 155 113 133 115 196 84 207 84 216 116 209 120 224 124 209 156 216 156 207 125 196 127 133 213 155 212 144 128 109 128 49C128 34 125 16 120 16Z M101 158C96 158 94 165 94 173L94 195 110 198 110 170C110 163 107 158 101 158Z M139 158C133 158 130 163 130 170L130 198 146 195 146 173C146 165 144 158 139 158Z M107 176L117 176 117 184 107 184Z M123 176L133 176 133 184 123 184Z M120 173C114 173 111 180 111 188L111 213 129 213 129 188C129 180 126 173 120 173Z'
  },
  jet: {
    name: 'TWIN-ENGINE JET',
    path: 'M120 16C114 16 109 34 109 49L109 98 20 143 20 155 109 131 111 190 81 211 81 219 116 208 120 225 124 208 159 219 159 211 129 190 131 131 220 155 220 143 131 98 131 49C131 34 126 16 120 16Z M73 111C69 111 67 116 67 124L67 148 79 148 79 124C79 116 77 111 73 111Z M167 111C163 111 161 116 161 124L161 148 173 148 173 124C173 116 171 111 167 111Z'
  },
  fourEngine: {
    name: 'FOUR-ENGINE JET',
    path: 'M120 15C112 15 106 34 106 51L106 96 20 142 20 155 105 133 109 189 77 211 77 219 115 207 120 224 125 207 163 219 163 211 131 189 135 133 220 155 220 142 134 96 134 51C134 34 128 15 120 15Z M46 126C42 126 40 130 40 137L40 156 52 156 52 137C52 130 50 126 46 126Z M77 109C73 109 71 114 71 121L71 147 83 147 83 121C83 114 81 109 77 109Z M163 109C159 109 157 114 157 121L157 147 169 147 169 121C169 114 167 109 163 109Z M194 126C190 126 188 130 188 137L188 156 200 156 200 137C200 130 198 126 194 126Z'
  },
  turboprop: {
    name: 'TWIN TURBOPROP',
    path: 'M120 24C114 24 109 39 109 52L109 98 25 103 25 121 109 121 113 190 85 199 85 210 116 204 120 218 124 204 155 210 155 199 127 190 131 121 215 121 215 103 131 98 131 52C131 39 126 24 120 24Z M73 92C68 92 66 102 66 110L66 136 80 136 80 110C80 102 78 92 73 92Z M167 92C162 92 160 102 160 110L160 136 174 136 174 110C174 102 172 92 167 92Z M52 88L94 88 94 94 52 94Z M146 88L188 88 188 94 146 94Z'
  },
  fourTurboprop: {
    name: 'FOUR-ENGINE TURBOPROP',
    path: 'M120 24C113 24 107 39 107 53L107 97 20 102 20 121 108 121 112 187 81 199 81 211 116 204 120 218 124 204 159 211 159 199 128 187 132 121 220 121 220 102 133 97 133 53C133 39 127 24 120 24Z M47 93C43 93 40 101 40 108L40 135 54 135 54 108C54 101 51 93 47 93Z M78 89C74 89 71 98 71 106L71 135 85 135 85 106C85 98 82 89 78 89Z M162 89C158 89 155 98 155 106L155 135 169 135 169 106C169 98 166 89 162 89Z M193 93C189 93 186 101 186 108L186 135 200 135 200 108C200 101 197 93 193 93Z M32 89L62 89 62 95 32 95Z M63 85L93 85 93 91 63 91Z M147 85L177 85 177 91 147 91Z M178 89L208 89 208 95 178 95Z'
  },
  light: {
    name: 'LIGHT PROPELLER AIRCRAFT',
    path: 'M120 31C113 31 109 45 109 58L109 96 26 99 26 116 109 118 114 182 88 190 88 201 116 198 120 214 124 198 152 201 152 190 126 182 131 118 214 116 214 99 131 96 131 58C131 45 127 31 120 31Z M91 29L149 29 149 35 91 35Z'
  },
  helicopter: {
    name: 'HELICOPTER',
    path: 'M120 52C108 52 101 71 101 93L101 120C101 132 107 143 114 147L116 204 107 211 107 216 119 213 120 222 121 213 133 216 133 211 124 204 126 147C133 143 139 132 139 120L139 93C139 71 132 52 120 52Z M116 20L124 20 124 195 116 195Z M21 96L219 96 219 104 21 104Z M86 86L93 86 93 143 86 143Z M147 86L154 86 154 143 147 143Z M92 111L107 111 107 117 92 117Z M133 111L148 111 148 117 133 117Z M103 201L137 201 137 207 103 207Z'
  },
  generic: {
    name: 'AIRCRAFT',
    path: 'M120 21C115 21 111 35 111 49L111 99 24 139 24 150 111 128 114 190 85 207 85 216 117 205 120 221 123 205 155 216 155 207 126 190 129 128 216 150 216 139 129 99 129 49C129 35 125 21 120 21Z'
  }
};

// Explicit designators avoid guessing engine count from a manufacturer prefix
// or ADS-B weight category (a heavy aircraft can still have only two engines).
const fourEngineTypes = new Set([
  'B747', 'A340', 'A380',
  'B741', 'B742', 'B743', 'B744', 'B748', 'B74R', 'B74S', 'B74D',
  'A342', 'A343', 'A345', 'A346', 'A388', 'IL96', 'A124'
]);
const boeing737Types = new Set([
  'B731', 'B732', 'B733', 'B734', 'B735', 'B736', 'B737', 'B738', 'B739',
  'B37M', 'B38M', 'B39M', 'B3XM'
]);
const challengerTypes = new Set(['CL30', 'CL35']);
const businessJetTypes = new Set([
  'C25A', 'C25B', 'C25C', 'C510', 'C525', 'C550', 'C560', 'C56X',
  'C680', 'C68A', 'C700', 'C750', 'GLF4', 'GLF5', 'GLF6', 'GLEX',
  'GL5T', 'CL60'
]);
const regionalJetTypes = new Set(['CRJ1', 'CRJ2', 'CRJ7', 'CRJ9', 'CRJX', 'E135', 'E145']);
const triJetTypes = new Set(['DC10', 'MD11']);
const rearTriJetTypes = new Set(['B721', 'B722', 'FA50', 'F900', 'FA7X', 'FA8X']);
const fourTurbopropTypes = new Set(['C130', 'C30J', 'L382', 'P3', 'L188', 'A400', 'AN12']);
const twinJetTypes = new Set([
  'A318', 'A319', 'A320', 'A321', 'A19N', 'A20N', 'A21N',
  'A332', 'A333', 'A338', 'A339', 'A359', 'A35K',
  'B752', 'B753', 'B762', 'B763', 'B764',
  'B772', 'B773', 'B77L', 'B77W', 'B788', 'B789', 'B78X',
  'BCS1', 'BCS3', 'E170', 'E175', 'E75L', 'E75S', 'E190', 'E195', 'E290', 'E295'
]);
const twinTurbopropTypes = new Set([
  'AT43', 'AT45', 'AT46', 'AT72', 'AT73', 'AT75', 'AT76',
  'DH8A', 'DH8B', 'DH8C', 'DH8D', 'SF34', 'SB20', 'BE20', 'BE30',
  'B350', 'B190', 'DHC6', 'C212', 'CN35', 'C295'
]);
const lightPropTypes = new Set([
  'C150', 'C152', 'C162', 'C172', 'C177', 'C182', 'C185', 'C206', 'C210',
  'C208', 'PC12', 'PC6T', 'TBM7', 'TBM8', 'TBM9', 'SR20', 'SR22',
  'P28A', 'P28B', 'P28R', 'P28T', 'PA32', 'PA46', 'DA20', 'DA40',
  'M20P', 'M20T', 'BE33', 'BE35', 'BE36'
]);
const helicopterTypes = new Set([
  'R22', 'R44', 'R66', 'B06', 'B407', 'B412', 'B429', 'B505',
  'EC20', 'EC25', 'EC30', 'EC35', 'EC45', 'EC55', 'EC75',
  'H135', 'H145', 'H160', 'H175', 'H215', 'H225',
  'AS32', 'AS50', 'AS55', 'AS65', 'A109', 'A119', 'A139', 'A169', 'A189',
  'S61', 'S76', 'S92', 'H60', 'H64'
]);

const aircraftModelNames = {
  A318: 'Airbus A318', A319: 'Airbus A319', A320: 'Airbus A320', A321: 'Airbus A321',
  A19N: 'Airbus A319neo', A20N: 'Airbus A320neo', A21N: 'Airbus A321neo',
  A332: 'Airbus A330-200', A333: 'Airbus A330-300',
  A338: 'Airbus A330-800neo', A339: 'Airbus A330-900neo',
  A340: 'Airbus A340 family', A342: 'Airbus A340-200', A343: 'Airbus A340-300',
  A345: 'Airbus A340-500', A346: 'Airbus A340-600',
  A359: 'Airbus A350-900', A35K: 'Airbus A350-1000',
  A380: 'Airbus A380 family', A388: 'Airbus A380-800',
  BCS1: 'Airbus A220-100', BCS3: 'Airbus A220-300',
  B721: 'Boeing 727-100', B722: 'Boeing 727-200',
  B731: 'Boeing 737-100', B732: 'Boeing 737-200', B733: 'Boeing 737-300',
  B734: 'Boeing 737-400', B735: 'Boeing 737-500', B736: 'Boeing 737-600',
  B737: 'Boeing 737-700', B738: 'Boeing 737-800', B739: 'Boeing 737-900',
  B37M: 'Boeing 737 MAX 7', B38M: 'Boeing 737 MAX 8',
  B39M: 'Boeing 737 MAX 9', B3XM: 'Boeing 737 MAX 10',
  B747: 'Boeing 747 family', B741: 'Boeing 747-100', B742: 'Boeing 747-200',
  B743: 'Boeing 747-300', B744: 'Boeing 747-400', B748: 'Boeing 747-8',
  B74R: 'Boeing 747SR', B74S: 'Boeing 747SP', B74D: 'Boeing 747-400D',
  B752: 'Boeing 757-200', B753: 'Boeing 757-300',
  B762: 'Boeing 767-200', B763: 'Boeing 767-300', B764: 'Boeing 767-400',
  B772: 'Boeing 777-200', B773: 'Boeing 777-300',
  B77L: 'Boeing 777-200LR/F', B77W: 'Boeing 777-300ER',
  B788: 'Boeing 787-8', B789: 'Boeing 787-9', B78X: 'Boeing 787-10',
  DC10: 'McDonnell Douglas DC-10', MD11: 'McDonnell Douglas MD-11',
  IL96: 'Ilyushin Il-96', A124: 'Antonov An-124 Ruslan',
  E135: 'Embraer ERJ 135', E145: 'Embraer ERJ 145',
  E170: 'Embraer E170', E175: 'Embraer E175', E75L: 'Embraer E175', E75S: 'Embraer E175',
  E190: 'Embraer E190', E195: 'Embraer E195', E290: 'Embraer E190-E2', E295: 'Embraer E195-E2',
  CRJ1: 'Bombardier CRJ100', CRJ2: 'Bombardier CRJ200', CRJ7: 'Bombardier CRJ700',
  CRJ9: 'Bombardier CRJ900', CRJX: 'Bombardier CRJ1000',
  C25A: 'Cessna Citation CJ2', C25B: 'Cessna Citation CJ3', C25C: 'Cessna Citation CJ4',
  C510: 'Cessna Citation Mustang', C525: 'Cessna CitationJet/CJ1',
  C550: 'Cessna Citation II/Bravo', C560: 'Cessna Citation V/Ultra/Encore',
  C56X: 'Cessna Citation Excel/XLS', C680: 'Cessna Citation Sovereign',
  C68A: 'Cessna Citation Latitude', C700: 'Cessna Citation Longitude', C750: 'Cessna Citation X/X+',
  GLF4: 'Gulfstream IV family', GLF5: 'Gulfstream V/G550 family', GLF6: 'Gulfstream G650/G650ER',
  GLEX: 'Bombardier Global Express family', GL5T: 'Bombardier Global 5000',
  CL30: 'Bombardier Challenger 300', CL35: 'Bombardier Challenger 350/3500',
  CL60: 'Bombardier Challenger 600 series',
  FA50: 'Dassault Falcon 50', F900: 'Dassault Falcon 900',
  FA7X: 'Dassault Falcon 7X', FA8X: 'Dassault Falcon 8X',
  AT43: 'ATR 42-300/320', AT45: 'ATR 42-500', AT46: 'ATR 42-600',
  AT72: 'ATR 72-100/200', AT73: 'ATR 72-210 series',
  AT75: 'ATR 72-500', AT76: 'ATR 72-600',
  DH8A: 'De Havilland Canada Dash 8-100', DH8B: 'De Havilland Canada Dash 8-200',
  DH8C: 'De Havilland Canada Dash 8-300', DH8D: 'De Havilland Canada Dash 8-400',
  SF34: 'Saab 340', SB20: 'Saab 2000',
  BE20: 'Beechcraft King Air 200', BE30: 'Beechcraft King Air 300',
  B350: 'Beechcraft King Air 350', B190: 'Beechcraft 1900',
  DHC6: 'De Havilland Canada DHC-6 Twin Otter', C212: 'CASA C-212 Aviocar',
  CN35: 'CASA/IPTN CN-235', C295: 'CASA C-295',
  C130: 'Lockheed C-130 Hercules', C30J: 'Lockheed Martin C-130J Super Hercules',
  L382: 'Lockheed L-100 Hercules', P3: 'Lockheed P-3 Orion', L188: 'Lockheed L-188 Electra',
  A400: 'Airbus A400M Atlas', AN12: 'Antonov An-12',
  C150: 'Cessna 150', C152: 'Cessna 152', C162: 'Cessna 162 Skycatcher',
  C172: 'Cessna 172 Skyhawk', C177: 'Cessna 177 Cardinal', C182: 'Cessna 182 Skylane',
  C185: 'Cessna 185 Skywagon', C206: 'Cessna 206 Stationair',
  C210: 'Cessna 210 Centurion', C208: 'Cessna 208 Caravan',
  PC12: 'Pilatus PC-12', PC6T: 'Pilatus PC-6 Turbo Porter',
  TBM7: 'Daher TBM 700', TBM8: 'Daher TBM 850', TBM9: 'Daher TBM 900 series',
  SR20: 'Cirrus SR20', SR22: 'Cirrus SR22',
  P28A: 'Piper PA-28 Cherokee/Warrior/Archer', P28B: 'Piper PA-28 Cherokee 235/Dakota',
  P28R: 'Piper PA-28 Arrow', P28T: 'Piper PA-28 Turbo Arrow',
  PA32: 'Piper PA-32 Cherokee Six/Saratoga', PA46: 'Piper PA-46 Malibu/Mirage',
  DA20: 'Diamond DA20 Katana/Eclipse', DA40: 'Diamond DA40 Diamond Star',
  M20P: 'Mooney M20', M20T: 'Mooney M20 turbocharged',
  BE33: 'Beechcraft Debonair/Bonanza 33', BE35: 'Beechcraft Bonanza 35', BE36: 'Beechcraft Bonanza 36',
  R22: 'Robinson R22', R44: 'Robinson R44', R66: 'Robinson R66',
  B06: 'Bell 206 JetRanger/LongRanger', B407: 'Bell 407', B412: 'Bell 412',
  B429: 'Bell 429', B505: 'Bell 505 Jet Ranger X',
  EC20: 'Airbus H120/Eurocopter EC120', EC25: 'Airbus H225/Eurocopter EC225',
  EC30: 'Airbus H130/Eurocopter EC130', EC35: 'Airbus H135/Eurocopter EC135',
  EC45: 'Airbus H145/Eurocopter EC145', EC55: 'Airbus H155/Eurocopter EC155',
  EC75: 'Airbus H175/Eurocopter EC175',
  H135: 'Airbus H135', H145: 'Airbus H145', H160: 'Airbus H160',
  H175: 'Airbus H175', H215: 'Airbus H215', H225: 'Airbus H225',
  AS32: 'Aerospatiale AS332 Super Puma', AS50: 'Airbus H125/Aerospatiale AS350',
  AS55: 'Aerospatiale AS355 Twin Squirrel', AS65: 'Aerospatiale AS365 Dauphin',
  A109: 'Leonardo AW109', A119: 'Leonardo AW119 Koala',
  A139: 'Leonardo AW139', A169: 'Leonardo AW169', A189: 'Leonardo AW189',
  S61: 'Sikorsky S-61', S76: 'Sikorsky S-76', S92: 'Sikorsky S-92',
  H60: 'Sikorsky H-60 family', H64: 'Boeing AH-64 Apache'
};

function hasAircraftType(type) {
  return type && type !== '---' && type !== 'UNKNOWN';
}

function aircraftModelName(plane) {
  if (!plane) return '';
  const type = String(plane.type || '').trim().toUpperCase();
  if (hasAircraftType(type)) return aircraftModelNames[type] || '';

  // A reported designator always wins, including when it is unfamiliar.
  const description = String(plane.description || '').trim().toUpperCase();
  const boeing = description.match(/\b(?:BOEING[ -]*)?B?737(?:[ -]*(?:MAX[ -]*(7|8|9|10)|([1-9]00)))?\b/);
  if (boeing) return boeing[1] ? `Boeing 737 MAX ${boeing[1]}` : boeing[2] ? `Boeing 737-${boeing[2]}` : 'Boeing 737 family';
  const challenger = description.match(/\bCHALLENGER[ -]*(300|3500|350|600|601|604|605|650)\b/);
  if (challenger) return `Bombardier Challenger ${challenger[1]}`;
  return '';
}

// Families deliberately group variants that a broad source description cannot
// distinguish. A 737's explicit -700/-800/MAX model remains useful evidence.
const aircraftIdentityGroups = [
  ['B727', ['B721', 'B722']],
  ['B747', ['B747', 'B741', 'B742', 'B743', 'B744', 'B748', 'B74R', 'B74S', 'B74D']],
  ['B757', ['B752', 'B753']], ['B767', ['B762', 'B763', 'B764']],
  ['B777', ['B772', 'B773', 'B77L', 'B77W']], ['B787', ['B788', 'B789', 'B78X']],
  ['A220', ['BCS1', 'BCS3']], ['A319', ['A319', 'A19N']],
  ['A320', ['A320', 'A20N']], ['A321', ['A321', 'A21N']],
  ['A330', ['A332', 'A333', 'A338', 'A339']],
  ['A340', ['A340', 'A342', 'A343', 'A345', 'A346']],
  ['A350', ['A359', 'A35K']], ['A380', ['A380', 'A388']],
  ['E175', ['E175', 'E75L', 'E75S']], ['E190', ['E190', 'E290']], ['E195', ['E195', 'E295']],
  ['C130', ['C130', 'C30J', 'L382']],
  ['EC25', ['EC25', 'H225']], ['EC35', ['EC35', 'H135']],
  ['EC45', ['EC45', 'H145']], ['EC75', ['EC75', 'H175']]
];

function aircraftTypeIdentity(type) {
  if (!aircraftModelNames[type]) return null;
  if (boeing737Types.has(type)) {
    return {family: 'B737', model: aircraftModelNames[type].replace('Boeing 737', '').replace(/[ -]/g, '')};
  }
  const group = aircraftIdentityGroups.find(entry => entry[1].includes(type));
  return {family: group ? group[0] : type, model: ''};
}

function aircraftIdentityWarning(plane) {
  if (!plane) return '';
  const type = String(plane.type || '').trim().toUpperCase();
  const reported = aircraftTypeIdentity(type);
  if (!reported) return '';
  const rawDescription = String(plane.description || '').trim();
  const description = rawDescription.toUpperCase();
  const identities = [];
  let match;
  const codes = /\b[A-Z][A-Z0-9]{1,4}\b/g;
  while ((match = codes.exec(description))) {
    // B737-800 is model shorthand, not the ICAO code B737 (737-700).
    if (match[0] === 'B737' && /^[ -]*(?:MAX[ -]*(?:7|8|9|10)|[1-9]00)\b/.test(description.slice(match.index + 4))) continue;
    if (match[0] === 'B737' && !/\bICAO(?:[ -]+(?:TYPE|CODE))?[: -]*$/.test(description.slice(0, match.index))) {
      // In descriptive prose B737 can mean the entire 737 family.
      identities.push({family: 'B737', model: ''});
      continue;
    }
    const identity = aircraftTypeIdentity(match[0]);
    if (identity) identities.push(identity);
  }
  const boeing737 = /\b(?:BOEING[ -]*|B[ -]*)?737(?:[ -]*(?:MAX[ -]*(7|8|9|10)|([1-9]00)))?\b/g;
  while ((match = boeing737.exec(description))) {
    identities.push({family: 'B737', model: match[1] ? `MAX${match[1]}` : match[2] || ''});
  }
  const boeing = /\b(?:BOEING[ -]*|B[ -]*)(727|747|757|767|777|787)\b/g;
  while ((match = boeing.exec(description))) identities.push({family: `B${match[1]}`, model: ''});
  const airbus = /\b(?:AIRBUS[ -]*A?|A)(220|318|319|320|321|330|340|350|380)(?:[ -]*NEO)?\b/g;
  while ((match = airbus.exec(description))) identities.push({family: `A${match[1]}`, model: ''});
  const challenger = /\bCHALLENGER[ -]*(300|3500|350|600|601|604|605|650)\b/g;
  while ((match = challenger.exec(description))) {
    identities.push({family: match[1] === '300' ? 'CL30' : /^350/.test(match[1]) ? 'CL35' : 'CL60', model: ''});
  }
  const crj = /\bCRJ[ -]*(1000|100|200|700|900)\b/g;
  const crjCodes = {'100': 'CRJ1', '200': 'CRJ2', '700': 'CRJ7', '900': 'CRJ9', '1000': 'CRJX'};
  while ((match = crj.exec(description))) identities.push({family: crjCodes[match[1]], model: ''});
  const embraer = /\b(?:EMBRAER[ -]*(?:ERJ[ -]*)?|E(?:RJ)?[ -]*)(135|145|170|175|190|195)(?:[ -]*E2)?\b/g;
  while ((match = embraer.exec(description))) identities.push({family: `E${match[1]}`, model: ''});
  const falcon = /\bFALCON[ -]*(50|900|7X|8X)\b/g;
  const falconCodes = {'50': 'FA50', '900': 'F900', '7X': 'FA7X', '8X': 'FA8X'};
  while ((match = falcon.exec(description))) identities.push({family: falconCodes[match[1]], model: ''});
  const douglas = /\b(DC[ -]*10|MD[ -]*11)\b/g;
  while ((match = douglas.exec(description))) identities.push({family: match[1].replace(/[ -]/g, ''), model: ''});

  // Multiple different models in a description are ambiguous, not evidence.
  const families = Array.from(new Set(identities.map(identity => identity.family)));
  const models = Array.from(new Set(identities.map(identity => identity.model).filter(Boolean)));
  if (families.length !== 1 || models.length > 1) return '';
  const familyConflict = families[0] !== reported.family;
  const modelConflict = models.length === 1 && reported.model && models[0] !== reported.model;
  if (!familyConflict && !modelConflict) return '';
  return `Reported type ${type} (${aircraftModelNames[type]}) conflicts with source description "${rawDescription}".`;
}

function aircraftProfile(plane) {
  if (!plane) return aircraftSilhouettes.generic;
  const type = String(plane.type || '').trim().toUpperCase();
  const category = String(plane.category || '').trim().toUpperCase();
  if (helicopterTypes.has(type)) return aircraftSilhouettes.helicopter;
  if (boeing737Types.has(type)) return aircraftSilhouettes.boeing737;
  if (challengerTypes.has(type)) return aircraftSilhouettes.challenger;
  if (businessJetTypes.has(type)) return aircraftSilhouettes.businessJet;
  if (regionalJetTypes.has(type)) return aircraftSilhouettes.regionalJet;
  if (triJetTypes.has(type)) return aircraftSilhouettes.triJet;
  if (rearTriJetTypes.has(type)) return aircraftSilhouettes.rearTriJet;
  if (fourEngineTypes.has(type)) return aircraftSilhouettes.fourEngine;
  if (twinJetTypes.has(type)) return aircraftSilhouettes.jet;
  if (twinTurbopropTypes.has(type)) return aircraftSilhouettes.turboprop;
  if (fourTurbopropTypes.has(type)) return aircraftSilhouettes.fourTurboprop;
  if (lightPropTypes.has(type)) return aircraftSilhouettes.light;

  // An unfamiliar real type stays generic. Descriptions are only a fallback
  // when the source did not identify a model, never a reason to override one.
  if (hasAircraftType(type)) return aircraftSilhouettes.generic;
  if (category === 'A7') return aircraftSilhouettes.helicopter;
  const description = String(plane.description || '').trim().toUpperCase();
  if (/\b(HELICOPTER|ROTORCRAFT|ROBINSON|EUROCOPTER)\b/.test(description)) return aircraftSilhouettes.helicopter;
  if (/\b(?:BOEING[ -]*)?B?737\b/.test(description)) return aircraftSilhouettes.boeing737;
  if (/\bCHALLENGER[ -]*(300|350|3500)\b/.test(description)) return aircraftSilhouettes.challenger;
  if (/\b(CHALLENGER[ -]*(600|601|604|605|650)|CITATION|GULFSTREAM)\b/.test(description)) return aircraftSilhouettes.businessJet;
  if (/\b(CRJ[ -]*(1000|100|200|700|900)|(?:EMBRAER[ -]*)?ERJ[ -]*(135|145))\b/.test(description)) return aircraftSilhouettes.regionalJet;
  if (/\b((?:B(?:OEING)?[ -]*)?727|FALCON[ -]*(50|900|7X|8X))\b/.test(description)) return aircraftSilhouettes.rearTriJet;
  if (/\b(DC[ -]*10|MD[ -]*11)\b/.test(description)) return aircraftSilhouettes.triJet;
  if (/\b(C[ -]*130J?|L[ -]*(100|188|382)|P[ -]*3|A[ -]*400M?|AN[ -]*12|FOUR[ -]*ENGINE[ -]*TURBOPROP)\b/.test(description)) return aircraftSilhouettes.fourTurboprop;
  if (/\b(B(?:OEING)?[ -]*747|(?:AIRBUS[ -]*)?A(?:340|380)|FOUR[ -]*ENGINE(?:D)?[ -]*JET)\b/.test(description)) return aircraftSilhouettes.fourEngine;
  if (/\b(TWIN[ -]*(?:ENGINE[ -]*)?TURBOPROP|ATR[ -]*(?:42|72)|DASH[ -]*8)\b/.test(description)) return aircraftSilhouettes.turboprop;
  if (/\b(CESSNA[ -]*(?:150|152|172|182|206|208|210)|CIRRUS[ -]*SR(?:20|22)|PIPER[ -]*(?:CHEROKEE|ARCHER)|SINGLE[ -]*ENGINE[ -]*(?:PROP|PISTON))\b/.test(description)) return aircraftSilhouettes.light;
  if (/\b(BOEING[ -]*(?:757|767|777|787)|AIRBUS[ -]*A(?:220|318|319|320|321|330|350)|TWIN[ -]*ENGINE[ -]*JET)\b/.test(description)) return aircraftSilhouettes.jet;
  return aircraftSilhouettes.generic;
}
