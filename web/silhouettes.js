// Original top-down family silhouettes, nose up, centered at (120, 120).
// Geometry stays inside a 108px radius so heading rotation cannot clip it.
const aircraftSilhouettes = {
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
const twinJetTypes = new Set([
  'A318', 'A319', 'A320', 'A321', 'A19N', 'A20N', 'A21N',
  'A332', 'A333', 'A338', 'A339', 'A359', 'A35K',
  'B731', 'B732', 'B733', 'B734', 'B735', 'B736', 'B737', 'B738', 'B739',
  'B37M', 'B38M', 'B39M', 'B3XM', 'B752', 'B753', 'B762', 'B763', 'B764',
  'B772', 'B773', 'B77L', 'B77W', 'B788', 'B789', 'B78X',
  'BCS1', 'BCS3', 'E170', 'E175', 'E190', 'E195', 'E290', 'E295',
  'CRJ1', 'CRJ2', 'CRJ7', 'CRJ9', 'CRJX', 'C25A', 'C25B', 'C25C',
  'C510', 'C525', 'C550', 'C560', 'C56X', 'C680', 'C68A', 'C700', 'C750',
  'GLF4', 'GLF5', 'GLF6', 'GLEX', 'GL5T', 'CL30', 'CL35', 'CL60'
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

function aircraftProfile(plane) {
  if (!plane) return aircraftSilhouettes.generic;
  const type = String(plane.type || '').trim().toUpperCase();
  const category = String(plane.category || '').trim().toUpperCase();
  if (category === 'A7' || helicopterTypes.has(type)) return aircraftSilhouettes.helicopter;
  if (fourEngineTypes.has(type)) return aircraftSilhouettes.fourEngine;
  if (twinJetTypes.has(type)) return aircraftSilhouettes.jet;
  if (twinTurbopropTypes.has(type)) return aircraftSilhouettes.turboprop;
  if (lightPropTypes.has(type)) return aircraftSilhouettes.light;

  // An unfamiliar real type stays generic. Descriptions are only a fallback
  // when the source did not identify a model, never a reason to override one.
  if (type && type !== '---' && type !== 'UNKNOWN') return aircraftSilhouettes.generic;
  const description = String(plane.description || '').trim().toUpperCase();
  if (/\b(HELICOPTER|ROTORCRAFT|ROBINSON|EUROCOPTER)\b/.test(description)) return aircraftSilhouettes.helicopter;
  if (/\b(B(?:OEING)?[ -]*747|(?:AIRBUS[ -]*)?A(?:340|380)|FOUR[ -]*ENGINE(?:D)?[ -]*JET)\b/.test(description)) return aircraftSilhouettes.fourEngine;
  if (/\b(TWIN[ -]*(?:ENGINE[ -]*)?TURBOPROP|ATR[ -]*(?:42|72)|DASH[ -]*8)\b/.test(description)) return aircraftSilhouettes.turboprop;
  if (/\b(CESSNA[ -]*(?:150|152|172|182|206|208|210)|CIRRUS[ -]*SR(?:20|22)|PIPER[ -]*(?:CHEROKEE|ARCHER)|SINGLE[ -]*ENGINE[ -]*(?:PROP|PISTON))\b/.test(description)) return aircraftSilhouettes.light;
  if (/\b(BOEING[ -]*(?:737|757|767|777|787)|AIRBUS[ -]*A(?:220|318|319|320|321|330|350)|TWIN[ -]*ENGINE[ -]*JET)\b/.test(description)) return aircraftSilhouettes.jet;
  return aircraftSilhouettes.generic;
}
