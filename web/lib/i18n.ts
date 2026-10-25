/** Interface copy in Spanish (default) and English. Numbers are formatted in lib/scale.ts. */

import type { Lang } from "./scale";

const es = {
  skip: "Saltar al mapa",
  campaign: "Campaña",
  index: "Índice",
  language: "Idioma",
  modeLabel: "Vista",
  modeSimple: "Sencilla",
  modeTechnical: "Técnica",
  greenness: "Verdor",
  thirst: "Sed",
  greennessName: "Verdor del olivar en primavera",
  thirstName: "Sed del olivar en verano",
  comparedWithUsual: "comparado con lo normal en cada municipio",
  greennessHelp:
    "Cuánto verdean los olivos de marzo a mayo, visto desde el satélite. Cada municipio se compara con sus otras campañas desde 2017.",
  thirstHelp:
    "Cuánta agua tienen las hojas de junio a agosto: más sed significa árboles con estrés por falta de agua. Cada municipio se compara con sus otras campañas desde 2017.",
  g0: "Mucho menos verde que lo normal",
  g1: "Menos verde que lo normal",
  g2: "Normal",
  g3: "Más verde que lo normal",
  g4: "Mucho más verde que lo normal",
  t0: "Mucha más sed que lo normal",
  t1: "Más sed que lo normal",
  t2: "Normal",
  t3: "Menos sed que lo normal",
  t4: "Mucha menos sed que lo normal",
  tShort0: "Mucha más sed",
  tShort1: "Más sed",
  tShort2: "Normal",
  tShort3: "Menos sed",
  tShort4: "Mucha menos sed",
  notEnoughHistory: "Sin historial suficiente",
  greennessSentence:
    "En la primavera de la campaña {campaign}, el olivar de {name} ha estado un {pct} {dir} verde que en sus otras campañas.",
  more: "más",
  less: "menos",
  thirstSentence: "En el verano de la campaña {campaign}, el olivar de {name} ha tenido {label}.",
  thirstUsual: "una sed normal, como en sus otras campañas",
  monthlyGreenness: "Verdor mes a mes",
  monthlyThirst: "Agua en las hojas mes a mes",
  harvestTitle: "Cosecha de aceite {campaign} en Jaén y Granada",
  harvestDetail:
    "Lo que prevé el aforo oficial de la Junta, en litros, kilos por hectárea y euros, y lo que ve el satélite.",
  harvestAforo: "Aforo oficial · Junta de Andalucía",
  harvestSatellite: "Estimación del satélite · experimental",
  harvestSatelliteNote:
    "En las campañas pasadas, el aforo acertó unas {ratio} veces más que el satélite: tómalo solo como orientación.",
  harvestValue: "Valor aproximado",
  litresColumn: "Aceite",
  kgPerHaColumn: "Por hectárea",
  harvestCaption:
    "Precio en origen (Poolred) del {start} al {end}: {low} €/kg (lampante) a {high} €/kg (virgen extra). 1 tonelada de aceite son unos 1.092 litros. Hectáreas de olivar: SIGPAC.",
  harvestCaptionNoPrice: "1 tonelada de aceite son unos 1.092 litros. Hectáreas de olivar: SIGPAC.",
  provincesTitleSimple: "Aceite producido en cada campaña",
  provincesLeadSimple:
    "Millones de litros de aceite: lo que se produjo de verdad, lo que dijo el aforo en octubre y lo que estimó el satélite sin conocer esa campaña.",
  methodTitleSimple: "¿De dónde salen estos datos?",
  method1Simple:
    "El verdor y la sed se miden con el satélite europeo Sentinel-2, que fotografía cada olivar cada pocos días. «Normal» es lo habitual en ese municipio desde 2017.",
  method2Simple:
    "La producción y el aforo son de la Junta de Andalucía. La estimación del satélite es un experimento: con solo 9 campañas aún no mejora al aforo, que cuenta aceituna en el campo.",
  showTechnical: "Ver los datos técnicos",
  satelliteShort: "Satélite (experimental)",
  satelliteForecast: "Previsión del satélite 2026/27 y su margen",
  millionLitres: "millones de litros",
  smallSample:
    "Ojo: solo se han podido medir {ha} ha de olivar en este municipio, así que un cambio en pocas parcelas (una plantación nueva, riego) mueve mucho la cifra.",
  themeToDark: "Cambiar a tema oscuro",
  themeToLight: "Cambiar a tema claro",
  question: "¿Puede el satélite anticipar la cosecha de aceite antes que el aforo oficial?",
  answer: "Todavía no.",
  answerDetail:
    "Con 9 campañas, OlivEye se queda en la media de cada provincia. El aforo de la Junta, que cuenta fruto en el campo en octubre, falla unas 3–4 veces menos.",
  forecastTitle: "Previsión OlivEye",
  forecastNote: "Datos hasta agosto · intervalo 80 %",
  aforoTitle: "Aforo oficial",
  aforoNote: "Junta de Andalucía · octubre 2026",
  mapeTitle: "Error porcentual absoluto medio (MAPE)",
  provinceMean: "Media de la provincia",
  modelErrorTitle: "Error medio de OlivEye",
  aforoErrorTitle: "Error medio del aforo",
  errorNote: "Mismas 15 provincias-campaña · validación dejando una campaña fuera",
  aforoCloser: "El aforo acertó más en {n} de {total} campañas",
  ndviName: "NDVI de primavera",
  ndmiName: "NDMI de verano",
  ndviShort: "NDVI",
  ndmiShort: "NDMI",
  ndviHelp:
    "NDVI mide el verdor de la vegetación (0 suelo desnudo, 1 vegetación muy densa). Media de marzo a mayo.",
  ndmiHelp:
    "NDMI mide el agua en las hojas: cuanto más bajo, más estrés hídrico. Media de junio a agosto.",
  mapTitle: "Olivar medido por el satélite",
  mapNote:
    "Cada forma es el olivar de un municipio: celdas de 250 m con al menos un 80 % de olivo según SIGPAC.",
  search: "Buscar municipio",
  searchEmpty: "Ningún municipio con ese nombre entre los 86 medidos.",
  sortValue: "Ordenar por valor",
  sortName: "Ordenar por nombre",
  municipalities: "{n} municipios",
  hectares: "ha de olivar",
  loadingMap: "Cargando el mapa…",
  mapError: "No se pudo cargar el mapa. Comprueba la conexión y recarga la página.",
  noData: "Sin dato",
  seriesTitle: "{name}: serie mensual",
  seriesHint: "Elige un municipio en la lista o en el mapa para ver sus 10 años de imágenes.",
  seriesWindow: "Meses que usa la campaña {campaign}",
  seriesLoading: "Cargando la serie…",
  seriesError: "No se pudo cargar la serie de este municipio.",
  close: "Cerrar",
  provincesTitle: "Producción de aceite por provincia",
  provincesLead:
    "Producción final, aforo oficial y estimación de OlivEye para cada campaña. Cada estimación se hizo sin ver esa campaña ni la siguiente.",
  real: "Producción final",
  aforo: "Aforo oficial",
  oliveye: "OlivEye",
  forecast: "Previsión 2026/27",
  interval: "Intervalo 80 %",
  selectedCampaign: "Campaña seleccionada",
  showTable: "Ver como tabla",
  hideTable: "Ocultar tabla",
  tonnes: "toneladas",
  derivedNote:
    "15 de las 16 producciones finales se calculan a partir de las variaciones que publica la Junta; la de 2025/26 es provisional.",
  errorsTitle: "Error en cada campaña",
  errorsLead:
    "Cuánto se alejó cada estimación de la producción final. Por encima de cero, la estimación se pasó; por debajo, se quedó corta. Las de OlivEye se hicieron sin ver esa campaña ni la siguiente.",
  errorsSummary:
    "OlivEye estuvo más cerca que el aforo en {n} de {total} provincias-campaña. Error absoluto medio (MAPE): OlivEye {model}, aforo {aforo}; repetir la producción de la campaña anterior, {last}.",
  errorsNote:
    "Solo cuentan las provincias-campaña con las dos estimaciones; las que no tienen aforo en nuestras fuentes se muestran, pero quedan fuera de la comparación. † Producción final calculada a partir de las variaciones que publica la Junta (no es una cifra publicada directamente). Fuente: Junta de Andalucía (aforos), AICA.",
  derivedMark: "† calculada",
  noAforo: "sin aforo",
  closer: "Más cerca: {who}",
  closerTie: "Empate",
  closerColumn: "Más cerca",
  methodTitle: "Cómo se ha validado",
  method1:
    "Cada campaña se predice con un modelo que no la vio, ni tampoco la siguiente, porque su «producción del año anterior» la delataría. Todos los modelos se comparan sobre las mismas filas.",
  method2:
    "Es un modelo Ridge con 4 variables fijadas de antemano: producción del año anterior, días de más de 32 °C en mayo, NDMI de verano y NDVI de primavera. Con tan pocos datos, el modelo descarta las variables y se queda en la media de cada provincia.",
  methodLink: "Resultados completos y limitaciones",
  sourcesTitle: "Fuentes",
  sources:
    "Copernicus Sentinel-2 L2A (openEO, CDSE) · SIGPAC (FEGA, Junta de Andalucía) · ERA5 vía Open-Meteo · Aforos y producción: Junta de Andalucía, AICA.",
  codeLink: "Código en GitHub",
  apiLink: "API",
  footerNote:
    "Proyecto de portafolio de José Antonio Nieto. Los datos se actualizan una vez por campaña.",
} as const;

export type MessageKey = keyof typeof es;

const en: Record<MessageKey, string> = {
  skip: "Skip to the map",
  campaign: "Campaign",
  index: "Index",
  language: "Language",
  modeLabel: "View",
  modeSimple: "Simple",
  modeTechnical: "Technical",
  greenness: "Greenness",
  thirst: "Thirst",
  greennessName: "Olive grove greenness in spring",
  thirstName: "Olive grove thirst in summer",
  comparedWithUsual: "compared with what is usual in each municipality",
  greennessHelp:
    "How green the olive trees are from March to May, seen from the satellite. Each municipality is compared with its other campaigns since 2017.",
  thirstHelp:
    "How much water the leaves hold from June to August: more thirst means trees stressed by lack of water. Each municipality is compared with its other campaigns since 2017.",
  g0: "Much less green than usual",
  g1: "Less green than usual",
  g2: "Usual",
  g3: "Greener than usual",
  g4: "Much greener than usual",
  t0: "Much thirstier than usual",
  t1: "Thirstier than usual",
  t2: "Usual",
  t3: "Less thirsty than usual",
  t4: "Much less thirsty than usual",
  tShort0: "Much thirstier",
  tShort1: "Thirstier",
  tShort2: "Usual",
  tShort3: "Less thirsty",
  tShort4: "Much less thirsty",
  notEnoughHistory: "Not enough history",
  greennessSentence:
    "In the spring of campaign {campaign}, {name}'s olive groves were {pct} {dir} green than in their other campaigns.",
  more: "more",
  less: "less",
  thirstSentence: "In the summer of campaign {campaign}, {name}'s olive groves were {label}.",
  thirstUsual: "as thirsty as in their other campaigns",
  monthlyGreenness: "Greenness month by month",
  monthlyThirst: "Leaf water month by month",
  harvestTitle: "Olive oil harvest {campaign} in Jaén and Granada",
  harvestDetail:
    "What the Junta's official forecast (aforo) expects, in litres, kilos per hectare and euros, and what the satellite sees.",
  harvestAforo: "Official forecast · Junta de Andalucía",
  harvestSatellite: "Satellite estimate · experimental",
  harvestSatelliteNote:
    "In past campaigns the official forecast was about {ratio} times more accurate than the satellite: take it as a rough guide only.",
  harvestValue: "Approximate value",
  litresColumn: "Oil",
  kgPerHaColumn: "Per hectare",
  harvestCaption:
    "Origin price (Poolred) {start} to {end}: €{low}/kg (lampante) to €{high}/kg (extra virgin). 1 tonne of oil is about 1,092 litres. Olive hectares: SIGPAC.",
  harvestCaptionNoPrice: "1 tonne of oil is about 1,092 litres. Olive hectares: SIGPAC.",
  provincesTitleSimple: "Olive oil produced each campaign",
  provincesLeadSimple:
    "Million litres of oil: what was actually produced, what the official forecast said in October, and what the satellite estimated without knowing that campaign.",
  methodTitleSimple: "Where do these figures come from?",
  method1Simple:
    "Greenness and thirst are measured by the European Sentinel-2 satellite, which photographs every olive grove every few days. 'Usual' is what is normal for that municipality since 2017.",
  method2Simple:
    "Production and the official forecast come from the Junta de Andalucía. The satellite estimate is an experiment: with only 9 campaigns it does not beat the official forecast yet, which counts olives in the field.",
  showTechnical: "See the technical data",
  satelliteShort: "Satellite (experimental)",
  satelliteForecast: "Satellite forecast 2026/27 and its margin",
  millionLitres: "million litres",
  smallSample:
    "Note: only {ha} ha of olive grove could be measured in this municipality, so a change in a few plots (a new plantation, irrigation) moves the figure a lot.",
  themeToDark: "Switch to dark theme",
  themeToLight: "Switch to light theme",
  question: "Can satellites forecast the olive oil harvest before the official forecast?",
  answer: "Not yet.",
  answerDetail:
    "With 9 campaigns, OlivEye reduces to each province's average. The Junta's official forecast (aforo), which counts fruit in the field in October, is about 3–4 times more accurate.",
  forecastTitle: "OlivEye forecast",
  forecastNote: "Data up to August · 80 % interval",
  aforoTitle: "Official forecast (aforo)",
  aforoNote: "Junta de Andalucía · October 2026",
  mapeTitle: "Mean absolute percentage error (MAPE)",
  provinceMean: "Province average",
  modelErrorTitle: "OlivEye mean error",
  aforoErrorTitle: "Aforo mean error",
  errorNote: "Same 15 province-campaigns · leave-one-campaign-out validation",
  aforoCloser: "The aforo was closer in {n} of {total} campaigns",
  ndviName: "Spring NDVI",
  ndmiName: "Summer NDMI",
  ndviShort: "NDVI",
  ndmiShort: "NDMI",
  ndviHelp:
    "NDVI measures how green vegetation is (0 bare soil, 1 very dense vegetation). March–May mean.",
  ndmiHelp: "NDMI measures water in the leaves: lower means more water stress. June–August mean.",
  mapTitle: "Olive groves measured by the satellite",
  mapNote:
    "Each shape is a municipality's olive area: 250 m cells with at least 80 % olive grove in SIGPAC.",
  search: "Search municipality",
  searchEmpty: "No municipality with that name among the 86 measured.",
  sortValue: "Sort by value",
  sortName: "Sort by name",
  municipalities: "{n} municipalities",
  hectares: "ha of olive grove",
  loadingMap: "Loading the map…",
  mapError: "The map could not be loaded. Check your connection and reload the page.",
  noData: "No data",
  seriesTitle: "{name}: monthly series",
  seriesHint: "Pick a municipality in the list or on the map to see 10 years of images.",
  seriesWindow: "Months used for campaign {campaign}",
  seriesLoading: "Loading the series…",
  seriesError: "The series for this municipality could not be loaded.",
  close: "Close",
  provincesTitle: "Olive oil production by province",
  provincesLead:
    "Final production, official forecast and OlivEye estimate per campaign. Each estimate was made without seeing that campaign or the next one.",
  real: "Final production",
  aforo: "Official forecast",
  oliveye: "OlivEye",
  forecast: "2026/27 forecast",
  interval: "80 % interval",
  selectedCampaign: "Selected campaign",
  showTable: "Show as table",
  hideTable: "Hide table",
  tonnes: "tonnes",
  derivedNote:
    "15 of the 16 final figures are back-calculated from the variations the Junta publishes; 2025/26 is provisional.",
  errorsTitle: "Error in each campaign",
  errorsLead:
    "How far each estimate was from the final production. Above zero the estimate was too high; below zero, too low. OlivEye's estimates were made without seeing that campaign or the next one.",
  errorsSummary:
    "OlivEye was closer than the aforo in {n} of {total} province-campaigns. Mean absolute percentage error (MAPE): OlivEye {model}, aforo {aforo}; repeating last campaign's production, {last}.",
  errorsNote:
    "Only province-campaigns with both estimates count; those without an aforo in our sources are shown but left out of the comparison. † Final figure back-calculated from the variations the Junta publishes (not a figure published directly). Source: Junta de Andalucía (aforos), AICA.",
  derivedMark: "† back-calculated",
  noAforo: "no aforo",
  closer: "Closer: {who}",
  closerTie: "Tie",
  closerColumn: "Closer",
  methodTitle: "How it was validated",
  method1:
    "Each campaign is predicted by a model that never saw it, nor the next one, whose 'last year's production' would give it away. Every model is scored on the same rows.",
  method2:
    "A Ridge model with 4 features fixed in advance: last year's production, May days above 32 °C, summer NDMI and spring NDVI. With so little data, it drops the features and settles on each province's average.",
  methodLink: "Full results and limitations",
  sourcesTitle: "Sources",
  sources:
    "Copernicus Sentinel-2 L2A (openEO, CDSE) · SIGPAC (FEGA, Junta de Andalucía) · ERA5 via Open-Meteo · Forecasts and production: Junta de Andalucía, AICA.",
  codeLink: "Code on GitHub",
  apiLink: "API",
  footerNote: "Portfolio project by José Antonio Nieto. Data is updated once per campaign.",
};

export const MESSAGES: Record<Lang, Record<MessageKey, string>> = { es, en };

/** Message with `{placeholders}` filled in. */
export function t(
  lang: Lang,
  key: MessageKey,
  values: Record<string, string | number> = {},
): string {
  return MESSAGES[lang][key].replace(/\{(\w+)\}/g, (_, name: string) =>
    name in values ? String(values[name]) : `{${name}}`,
  );
}
