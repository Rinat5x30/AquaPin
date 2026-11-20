/* Builds AquaPin_presentation.pptx (Russian, 12 slides). Run: node build_deck.js */
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("C:/Users/ASUS/.claude/skills/synced/12f9bcf6-9119-428e-8456-bff47f4b0ed4_e0c99e70-2dd1-405b-98f5-263c62c7fc81/pptx/scripts/apply_theme.js");

const IMG = (f) => path.join(__dirname, "img", f);
const OUT = path.join(__dirname, "AquaPin_presentation.pptx");

const THEME = {
  name: "AquaPin",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1D2620", lt1: "FFFFFF", dk2: "5B655D", lt2: "F3EFE4",
    accent1: "1E6B8C", accent2: "1A9850", accent3: "8A5A00", accent4: "A50026",
    accent5: "E8F1F4", accent6: "D9D3C3", hlink: "1E6B8C", folHlink: "5B655D",
  },
};
const HEX = { water: "1E6B8C", muted: "8A9189", ink: "1D2620" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "AquaPin: совет по поливу по спутнику и погоде";
pres.subject = "Global Sustainability Challenge 2026-27";
const C = pres.SchemeColor;
const W = 13.33;
const M = 0.6;

async function icon(Icon, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Icon, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

/* ---------- layouts (one per slide frame) ---------- */
pres.defineSlideMaster({
  title: "TITLE_DARK",
  objects: [{ rect: { x: 0, y: 0, w: W, h: 7.5, fill: { color: C.text1 } } }],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: "FFFFFF" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: W - 2 * M, h: 1.3, fontFace: "Cambria", fontSize: 36, bold: true, color: C.text1, align: "left", valign: "top", margin: 0 }, text: "" } },
    { text: { text: "AquaPin · Global Sustainability Challenge 2026–27", options: { x: M, y: 7.05, w: 7, h: 0.3, fontFace: "Calibri", fontSize: 11, color: C.text2, margin: 0, isTextBox: true } } },
  ],
  slideNumber: { x: W - M - 0.8, y: 7.05, w: 0.8, h: 0.3, fontFace: "Calibri", fontSize: 11, color: C.text2, align: "right" },
});

/* ---------- helpers ---------- */
function note(slide, text) { slide.addNotes(text); }
function card(slide, x, y, w, h, name) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.12, fill: { color: C.accent5 }, line: { type: "none" }, objectName: name });
}
async function iconCircle(slide, Icon, x, y, d, name, fill = C.accent1) {
  slide.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" }, objectName: name + " circle" });
  slide.addImage({ data: await icon(Icon, "FFFFFF"), x: x + d * 0.22, y: y + d * 0.22, w: d * 0.56, h: d * 0.56, objectName: name, altText: name });
}
function txt(slide, text, opts) { slide.addText(text, { isTextBox: true, margin: 0, fontFace: "Calibri", ...opts }); }

async function build() {
  /* ===== 1. Title ===== */
  pres.addSection({ title: "Введение" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Введение" });
  txt(s, "AquaPin", { x: M, y: 1.5, w: 5.8, h: 1.1, fontFace: "Cambria", fontSize: 66, bold: true, color: C.background1, objectName: "Название" });
  txt(s, "Сколько воды нужно полю сегодня", { x: M, y: 2.75, w: 5.7, h: 1.2, fontFace: "Cambria", fontSize: 30, color: C.background1, objectName: "Подзаголовок" });
  txt(s, "Совет по поливу по спутниковым снимкам Sentinel-2 и погоде, с проверкой точности по измерениям", { x: M, y: 4.1, w: 5.6, h: 1.0, fontSize: 18, color: C.background2, objectName: "Описание" });
  txt(s, "Global Sustainability Challenge 2026–27 · Adaptation & Resilience: вода и продовольствие", { x: M, y: 6.3, w: 5.8, h: 0.6, fontSize: 14, color: C.background2, objectName: "Конкурс" });
  s.addImage({ path: IMG("s-desktop.png"), x: 6.55, y: 1.6, w: 6.2, h: 3.486, objectName: "Скриншот AquaPin", altText: "Скриншот AquaPin: карта NDVI поля, совет «Полив 105 мм» и график сезона", shadow: { type: "outer", color: "000000", opacity: 0.35, blur: 12, offset: 4, angle: 90 } });
  txt(s, "Реальный экран продукта: поле в Куринской низменности, день полива", { x: 6.55, y: 5.25, w: 6.2, h: 0.5, fontSize: 12, color: C.background2, objectName: "Подпись" });
  note(s, "Здравствуйте. AquaPin отвечает на один вопрос: сколько воды нужно этому полю сегодня. Мы берём спутниковые снимки Sentinel-2 и погоду, считаем водный баланс и даём совет. Главное отличие: мы показываем, как получен совет, и открыто говорим, насколько ему можно верить. На экране реальный экран продукта на реальных данных.");

  /* ===== 2. Problem ===== */
  pres.addSection({ title: "Проблема и решение" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Проблема и решение" });
  s.addText("Вода уходит на поля, а полив — на глаз", { placeholder: "title" });
  txt(s, "71%", { x: M, y: 1.95, w: 4.3, h: 1.6, fontFace: "Cambria", fontSize: 88, bold: true, color: C.accent1, objectName: "Статистика 71%" });
  txt(s, "всей забираемой в мире пресной воды идёт на сельское хозяйство", { x: M, y: 3.65, w: 4.3, h: 1.3, fontSize: 20, color: C.text1, objectName: "Пояснение 71%" });
  txt(s, "FAO AQUASTAT 2025, данные 2022 года", { x: M, y: 5.0, w: 4.3, h: 0.4, fontSize: 12, color: C.text2, objectName: "Источник 71%" });
  const rows2 = [
    [fa.FaEye, "Решают по привычке", "В исследовании в ЮАР только 18% фермеров пользуются объективными методами, остальные полагаются на опыт и интуицию"],
    [fa.FaUserSlash, "Знают об инструментах, но не пользуются", "О сервисе FruitLook слышали 86% фермеров, для полива его использует один"],
    [fa.FaHandshake, "Узкое место — доверие", "Советы часто непонятны и не учитывают, что нужно фермеру. Поэтому мы объясняем «почему» и показываем точность"],
  ];
  for (let i = 0; i < rows2.length; i++) {
    const y = 1.95 + i * 1.5;
    card(s, 5.4, y, 7.33, 1.3, "Карточка " + (i + 1));
    await iconCircle(s, rows2[i][0], 5.65, y + 0.28, 0.75, "Иконка " + (i + 1));
    txt(s, rows2[i][1], { x: 6.65, y: y + 0.12, w: 5.9, h: 0.4, fontSize: 18, bold: true, color: C.text1, objectName: "Заголовок " + (i + 1) });
    txt(s, rows2[i][2], { x: 6.65, y: y + 0.52, w: 5.9, h: 0.7, fontSize: 14, color: C.text1, valign: "top", objectName: "Текст " + (i + 1) });
  }
  txt(s, "Источники: FAO AQUASTAT 2025; Adendorff и др., 2021 (исследование внедрения ирригационных расписаний, ЮАР)", { x: M, y: 6.55, w: 12.1, h: 0.35, fontSize: 11, color: C.text2, objectName: "Источники" });
  note(s, "Сельское хозяйство забирает около 71% пресной воды в мире по данным FAO. При этом решения о поливе часто принимают по привычке. Исследования внедрения показывают: фермеры знают об инструментах, но не пользуются, в частности из-за непонятных советов. Поэтому наша ставка не просто совет, а понятный и проверяемый совет.");

  /* ===== 3. Solution ===== */
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Проблема и решение" });
  s.addText("AquaPin: пин на поле — совет на сегодня", { placeholder: "title" });
  const steps = [
    [fa.FaMapMarkerAlt, "1. Пин", "Точка на карте и радиус поля. Можно из браузера или геопозицией из Telegram"],
    [fa.FaSatellite, "2. Данные", "Снимки Sentinel-2 (зелёность растений) и погода Open-Meteo (испарение, дождь)"],
    [fa.FaTint, "3. Совет", "«Полить 22 мм» или «Полив не нужен», с уровнем уверенности и объяснением"],
  ];
  for (let i = 0; i < 3; i++) {
    const x = M + i * (3.85 + 0.29);
    card(s, x, 1.95, 3.85, 3.7, "Шаг " + (i + 1));
    await iconCircle(s, steps[i][0], x + 0.4, 2.3, 1.0, "Иконка шага " + (i + 1));
    txt(s, steps[i][1], { x: x + 0.4, y: 3.6, w: 3.1, h: 0.5, fontSize: 24, bold: true, fontFace: "Cambria", color: C.text1, objectName: "Заголовок шага " + (i + 1) });
    txt(s, steps[i][2], { x: x + 0.4, y: 4.2, w: 3.1, h: 1.3, fontSize: 16, color: C.text1, valign: "top", objectName: "Описание шага " + (i + 1) });
  }
  txt(s, "Браузер и Telegram · русский и английский · мобильный вид · демо работает без интернета", { x: M, y: 6.05, w: 12.1, h: 0.5, fontSize: 18, color: C.text2, objectName: "Каналы" });
  note(s, "Пользователь ставит пин на своё поле и указывает радиус. Система берёт свежие снимки Sentinel-2 и погоду и отвечает: полить столько-то миллиметров или полив не нужен. Тот же ответ приходит в Telegram. Демо-примеры работают без интернета, это важно для показа.");

  /* ===== 4. Method ===== */
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Проблема и решение" });
  s.addText("От зелёности поля до миллиметров воды", { placeholder: "title" });
  const flow = [
    ["Снимок", "Sentinel-2: красный и ближний инфракрасный каналы"],
    ["NDVI", "(NIR − Red) / (NIR + Red); облака, тени, снег отсеяны"],
    ["Kcb", "сколько воды пьёт культура; границы по таблицам FAO-56"],
    ["Баланс воды", "дефицит в корнях: расход, дождь, полив (пакет pyfao56)"],
    ["Совет", "дефицит достиг порога: «Полив X мм»; иначе «не нужен»"],
  ];
  for (let i = 0; i < flow.length; i++) {
    const x = M + i * (2.2 + 0.28);
    card(s, x, 1.95, 2.2, 2.6, "Этап " + (i + 1));
    txt(s, String(i + 1), { x: x + 0.2, y: 2.1, w: 0.6, h: 0.5, fontSize: 24, bold: true, fontFace: "Cambria", color: C.accent1, objectName: "Номер " + (i + 1) });
    txt(s, flow[i][0], { x: x + 0.2, y: 2.65, w: 1.85, h: 0.45, fontSize: 20, bold: true, color: C.text1, objectName: "Название этапа " + (i + 1) });
    txt(s, flow[i][1], { x: x + 0.2, y: 3.15, w: 1.85, h: 1.3, fontSize: 14, color: C.text1, valign: "top", objectName: "Описание этапа " + (i + 1) });
    if (i < flow.length - 1) s.addShape(pres.ShapeType.rightArrow, { x: x + 2.2 + 0.02, y: 3.0, w: 0.24, h: 0.3, fill: { color: C.accent1 }, line: { type: "none" }, objectName: "Стрелка " + (i + 1) });
  }
  card(s, M, 4.85, 12.13, 1.65, "Правило совета");
  txt(s, "Правило", { x: M + 0.3, y: 5.0, w: 3, h: 0.35, fontSize: 16, bold: true, color: C.accent1, objectName: "Правило заголовок" });
  txt(s, "Полив советуем, когда дефицит воды в корнях достиг порога, при котором растение начинает страдать. Если в прогнозе на 3 дня дождь покрывает половину дефицита, совет снимается.", { x: M + 0.3, y: 5.38, w: 6.5, h: 1.0, fontSize: 14, color: C.text1, valign: "top", objectName: "Правило текст" });
  txt(s, "Что мы не изобретали", { x: 7.5, y: 5.0, w: 4.9, h: 0.35, fontSize: 16, bold: true, color: C.accent1, objectName: "Не изобретали заголовок" });
  txt(s, "Физику баланса считает проверенный пакет pyfao56 по методике FAO-56. Наша часть — спутниковый Kcb, облачная маска и честная проверка.", { x: 7.5, y: 5.38, w: 5.0, h: 1.0, fontSize: 14, color: C.text1, valign: "top", objectName: "Не изобретали текст" });
  note(s, "Пять шагов. Снимок Sentinel-2, из него считаем NDVI, индекс зелёности. NDVI переводим в коэффициент Kcb, то есть сколько воды пьёт культура. Дальше стандартный водный баланс FAO-56. Когда дефицит достигает порога, советуем полив. Физику не переписывали, используем пакет pyfao56. Честно: перевод NDVI в Kcb это наша эвристика, и дальше я покажу, как мы её проверили.");

  /* ===== 5. Live example ===== */
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Проблема и решение" });
  s.addText("Реальное поле, реальные снимки, день полива", { placeholder: "title" });
  s.addImage({ path: IMG("s-desktop.png"), x: M, y: 1.8, w: 8.2, h: 4.61, objectName: "Скриншот примера", altText: "Пример поля в Куринской низменности: карта NDVI, совет «Полив 105 мм», график дефицита воды и дни полива", shadow: { type: "outer", color: "000000", opacity: 0.25, blur: 10, offset: 3, angle: 90 } });
  txt(s, "Куринская низменность, Азербайджан · сезон 2025–26 · реальные данные Sentinel-2 и Open-Meteo", { x: M, y: 6.5, w: 8.2, h: 0.35, fontSize: 11, color: C.text2, objectName: "Подпись примера" });
  const call5 = [
    [fa.FaMap, "Карта", "NDVI по снимкам; пунктир — поле"],
    [fa.FaChartLine, "График", "дефицит воды, порог и дни полива"],
    [fa.FaSlidersH, "Сезон", "ползунок и кнопки дней полива"],
    [fa.FaWifi, "Без интернета", "три примера работают офлайн"],
  ];
  for (let i = 0; i < 4; i++) {
    const y = 1.8 + i * 1.18;
    await iconCircle(s, call5[i][0], 9.2, y, 0.7, "Иконка " + call5[i][1]);
    txt(s, call5[i][1], { x: 10.1, y: y - 0.02, w: 2.6, h: 0.35, fontSize: 18, bold: true, color: C.text1, objectName: "Заголовок " + call5[i][1] });
    txt(s, call5[i][2], { x: 10.1, y: y + 0.36, w: 2.6, h: 0.7, fontSize: 14, color: C.text1, valign: "top", objectName: "Текст " + call5[i][1] });
  }
  note(s, "Это реальное поле. Цвета на карте показывают зелёность растений по снимку Sentinel-2. Внизу график: чёрная линия дефицит воды, пунктир порог, при котором мы советуем полив, столбики дождь, синие метки дни полива. Ползунок позволяет пройти сезон день за днём. Кнопки в панели справа переводят сразу на дни полива. Живой совет можно получить для любого пина, а демо работает без интернета.");

  /* ===== 6. Trust ===== */
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Проблема и решение" });
  s.addText("Совет, который можно проверить", { placeholder: "title" });
  s.addImage({ path: IMG("why-crop.png"), x: M, y: 1.75, w: 2.59, h: 4.7, objectName: "Панель Почему", altText: "Панель «Почему этот совет» с коэффициентом, дефицитом воды, порогом и проверкой точности", shadow: { type: "outer", color: "000000", opacity: 0.25, blur: 8, offset: 3, angle: 90 } });
  s.addImage({ path: IMG("mobile-final.png"), x: 3.55, y: 1.75, w: 2.127, h: 4.7, objectName: "Мобильная версия", altText: "Мобильная версия: карта, совет «Полив 22 мм», уверенность и дни полива", shadow: { type: "outer", color: "000000", opacity: 0.25, blur: 8, offset: 3, angle: 90 } });
  txt(s, "Слева — панель «Почему этот совет» с проверкой точности. Справа — мобильная версия.", { x: M, y: 6.55, w: 7.0, h: 0.3, fontSize: 11, color: C.text2, objectName: "Подпись" });
  const pts6 = [
    "«Почему»: коэффициент культуры, дефицит воды, порог полива, дождь в прогнозе, версия расчёта",
    "Уверенность падает, когда давно не было чистого снимка; без снимков считаем по таблице и говорим об этом",
    "Проверка точности показана прямо в карточке, вместе с известным завышением",
    "Тот же совет приходит в Telegram обычным текстом",
  ];
  s.addText(pts6.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < pts6.length - 1, paraSpaceAfter: 12 } })), { x: 6.3, y: 1.85, w: 6.43, h: 4.6, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 18, color: C.text1, valign: "top", objectName: "Тезисы доверия" });
  note(s, "Мы не прячем модель. В панели «Почему этот совет» видно коэффициент культуры, дефицит воды, порог и дождь. Уверенность зависит от возраста последнего чистого снимка. И главное: прямо в панели написано, как мы проверили точность, включая то, что модель завышает испарение. Это ответ на проблему доверия.");

  /* ===== 7. Backtest chart ===== */
  pres.addSection({ title: "Доказательства" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Доказательства" });
  s.addText("Сверили с измерениями потоковых башен", { placeholder: "title" });
  s.addChart(pres.charts.BAR, [
    { name: "Спутниковый Kcb (AquaPin)", labels: ["Все 20 сезонов", "Европа, без орошения (14)", "Китай, орошаемая (6)"], values: [1.0, 1.02, 0.94] },
    { name: "Лучшая табличная кривая FAO-56", labels: ["Все 20 сезонов", "Европа, без орошения (14)", "Китай, орошаемая (6)"], values: [1.15, 1.01, 1.4] },
  ], {
    x: M, y: 1.7, w: 7.7, h: 5.1, barDir: "col", barGrouping: "clustered",
    chartColors: [HEX.water, HEX.muted],
    showTitle: true, title: "Ошибка дневного испарения, RMSE, мм/день (меньше — лучше)", titleFontSize: 14, titleColor: HEX.ink, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", dataLabelFontSize: 14, dataLabelColor: HEX.ink, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: HEX.ink, catAxisLabelFontSize: 13, catAxisLabelFontFace: "+mn-lt",
    valAxisLabelColor: HEX.ink, valAxisLabelFontSize: 12, valAxisLabelFontFace: "+mn-lt", valAxisMinVal: 0, valAxisMaxVal: 1.8,
    valGridLine: { color: "E3E6E4", size: 0.75 }, catGridLine: { style: "none" },
    showLegend: true, legendPos: "b", legendFontSize: 13, legendColor: HEX.ink, legendFontFace: "+mn-lt", barGapWidthPct: 60,
  });
  const call7 = [
    [fa.FaClipboardCheck, "Протокол записан до расчёта", "модель не подгонялась под эти данные"],
    [fa.FaDatabase, "Открытые данные ICOS (CC-BY)", "6 станций: DE-Geb, FR-Gri, BE-Lon, DE-RuS, CN-Lch, CN-Yuc; сезоны с 2017 года"],
    [fa.FaChartBar, "По неделям ошибка меньше", "0.84 против 1.02 мм/день у таблицы"],
  ];
  for (let i = 0; i < 3; i++) {
    const y = 1.85 + i * 1.62;
    await iconCircle(s, call7[i][0], 8.7, y, 0.7, "Иконка " + (i + 1));
    txt(s, call7[i][1], { x: 9.6, y: y - 0.02, w: 3.2, h: 0.4, fontSize: 16, bold: true, color: C.text1, valign: "top", objectName: "Заголовок " + (i + 1) });
    txt(s, call7[i][2], { x: 9.6, y: y + 0.4, w: 3.2, h: 0.95, fontSize: 14, color: C.text1, valign: "top", objectName: "Текст " + (i + 1) });
  }
  note(s, "Мы сравнили расчётное испарение с измеренным на потоковых башнях: 20 сезонов пшеницы на 6 станциях, открытые данные ICOS. Протокол записали до расчёта и модель не подгоняли. Синие столбики наш спутниковый вариант, серые лучшая из двух табличных кривых. В целом ошибка меньше, 1.00 против 1.15 миллиметра в день. В орошаемом Китае разница заметная, 0.94 против 1.40. В Европе без орошения мы не лучше таблицы, 1.02 против 1.01.");

  /* ===== 8. Findings ===== */
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Доказательства" });
  s.addText("Что показала проверка", { placeholder: "title" });
  const stats = [
    ["−13…16%", "ошибка испарения против табличной кривой FAO-56, в среднем по 20 сезонам", C.accent1],
    ["9 из 20", "сезонов, где спутник лучше лучшей из двух таблиц; различие не значимо (p = 0.82)", C.accent3],
    ["+13…43%", "завышение испарения моделью относительно башен (с поправкой на баланс энергии и без неё)", C.accent3],
  ];
  for (let i = 0; i < 3; i++) {
    const x = M + i * (3.85 + 0.29);
    card(s, x, 1.85, 3.85, 3.0, "Показатель " + (i + 1));
    txt(s, stats[i][0], { x: x + 0.3, y: 2.05, w: 3.3, h: 1.1, fontFace: "Cambria", fontSize: 48, bold: true, color: stats[i][2], objectName: "Число " + (i + 1) });
    txt(s, stats[i][1], { x: x + 0.3, y: 3.25, w: 3.3, h: 1.5, fontSize: 16, color: C.text1, valign: "top", objectName: "Смысл " + (i + 1) });
  }
  card(s, M, 5.2, 12.13, 1.4, "Вывод");
  txt(s, [{ text: "Вывод: ", options: { bold: true, color: C.accent1 } }, { text: "польза заметна в орошаемых условиях; в Европе преимущество не доказано; завышение испарения означает, что совет может приходить раньше нужного. Это первая задача фазы Build." }], { x: M + 0.3, y: 5.35, w: 11.5, h: 1.1, fontSize: 18, color: C.text1, valign: "middle", objectName: "Вывод текст" });
  note(s, "Три цифры. Первая: в среднем ошибка меньше на 13–16 процентов. Вторая: но по сезонам спутник лучше лучшей таблицы лишь в 9 из 20, и это статистически не значимо. Третья: модель завышает испарение на 13–43 процента, значит совет может приходить раньше. Мы выносим это на слайд сами, потому что доверие строится на честности.");

  /* ===== 9. Limits ===== */
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Доказательства" });
  s.addText("Ограничения, о которых мы говорим сами", { placeholder: "title" });
  const limits = [
    "Нет тестовых станций в Азербайджане: проверено в Европе и Китае",
    "Сезоны двух китайских станций приняты по литературе, в данных нет записи о культуре",
    "Почва условная (суглинок), история поливов фермера системе неизвестна",
    "Перевод NDVI в Kcb — эвристика с неподогнанными границами 0.15 и 0.85",
    "Проверено испарение, а не количество воды для полива",
  ];
  for (let i = 0; i < limits.length; i++) {
    const y = 1.85 + i * 0.96;
    s.addShape(pres.ShapeType.ellipse, { x: M, y: y + 0.08, w: 0.6, h: 0.6, fill: { color: C.accent3 }, line: { type: "none" }, objectName: "Круг " + (i + 1) });
    txt(s, String(i + 1), { x: M, y: y + 0.08, w: 0.6, h: 0.6, fontSize: 20, bold: true, fontFace: "Cambria", color: C.background1, align: "center", valign: "middle", objectName: "Номер " + (i + 1) });
    txt(s, limits[i], { x: 1.5, y: y, w: 11.2, h: 0.76, fontSize: 20, color: C.text1, valign: "middle", objectName: "Ограничение " + (i + 1) });
  }
  note(s, "Пять ограничений. Мы не проверяли в Азербайджане: там нет открытых станций, это задача на Build. Два китайских сезона мы приняли по литературе. Почва условная. Перевод NDVI в Kcb это наша эвристика. И проверили мы испарение, а не количество воды для полива. Эти оговорки есть и в интерфейсе продукта.");

  /* ===== 10. Why trust ===== */
  pres.addSection({ title: "Качество и план" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Качество и план" });
  s.addText("Почему этому можно доверять", { placeholder: "title" });
  const trust = [
    [fa.FaGlobeEurope, "Открытые данные", "Sentinel-2, Open-Meteo, ICOS: без закрытых источников и ключей"],
    [fa.FaEye, "Прозрачность", "объяснение совета, версия расчёта, перечень допущений"],
    [fa.FaClipboardCheck, "Проверяемость", "протокол, отчёт и воспроизводимый бэктест в репозитории"],
    [fa.FaLock, "Безопасность", "согласие на хранение места, удаление данных, UUID, лимиты запросов"],
  ];
  for (let i = 0; i < 4; i++) {
    const y = 1.85 + i * 1.2;
    await iconCircle(s, trust[i][0], M, y, 0.8, "Иконка " + trust[i][1]);
    txt(s, trust[i][1], { x: 1.65, y: y - 0.02, w: 6.2, h: 0.4, fontSize: 20, bold: true, color: C.text1, objectName: "Заголовок " + trust[i][1] });
    txt(s, trust[i][2], { x: 1.65, y: y + 0.4, w: 6.2, h: 0.7, fontSize: 15, color: C.text1, valign: "top", objectName: "Текст " + trust[i][1] });
  }
  const stat10 = [["104", "автоматических теста"], ["20", "сезонов проверено по башням"], ["3", "офлайн-примера на реальных данных"]];
  for (let i = 0; i < 3; i++) {
    const y = 1.85 + i * 1.6;
    card(s, 8.6, y, 4.13, 1.4, "Показатель " + (i + 1));
    txt(s, stat10[i][0], { x: 8.85, y: y + 0.1, w: 1.6, h: 1.2, fontFace: "Cambria", fontSize: 48, bold: true, color: C.accent1, valign: "middle", objectName: "Число " + (i + 1) });
    txt(s, stat10[i][1], { x: 10.5, y: y + 0.1, w: 2.1, h: 1.2, fontSize: 16, color: C.text1, valign: "middle", objectName: "Подпись числа " + (i + 1) });
  }
  note(s, "Почему этому можно доверять. Данные открытые. Совет объясняется. Проверка воспроизводима: протокол и отчёт лежат в репозитории, цифры повторяются до знака. Безопасность: хранение места только с согласием, удаление в один клик, идентификаторы полей не угадываются, есть лимиты запросов. 104 автотеста.");

  /* ===== 11. Plan ===== */
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Качество и план" });
  s.addText("План на фазу Build: декабрь — февраль", { placeholder: "title" });
  const plan = [
    ["Декабрь", ["Публичный стенд: деплой, HTTPS, постоянный воркер", "Исправить завышение испарения и перепроверить на новых сезонах", "Telegram-бот на настоящем API"]],
    ["Январь", ["Данные для региона: станции, консультации агрономов", "Показать продукт 3–5 фермерам, записать, что непонятно", "Оценка эффекта без громких цифр"]],
    ["Февраль", ["Презентация и видео для финала", "Репетиция демо, финальные тесты", "Подготовка к региональному финалу"]],
  ];
  for (let i = 0; i < 3; i++) {
    const x = M + i * (3.85 + 0.29);
    card(s, x, 1.85, 3.85, 3.9, "Месяц " + (i + 1));
    txt(s, plan[i][0], { x: x + 0.3, y: 2.0, w: 3.3, h: 0.55, fontFace: "Cambria", fontSize: 26, bold: true, color: C.accent1, objectName: "Месяц " + plan[i][0] });
    s.addText(plan[i][1].map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < plan[i][1].length - 1, paraSpaceAfter: 10 } })), { x: x + 0.3, y: 2.7, w: 3.3, h: 2.9, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 16, color: C.text1, valign: "top", objectName: "Задачи " + plan[i][0] });
  }
  txt(s, "Региональные финалы: февраль — март 2027 · мировой финал: 20–21 мая 2027, Ханчжоу", { x: M, y: 6.1, w: 12.1, h: 0.4, fontSize: 14, color: C.text2, objectName: "Календарь" });
  note(s, "План на Build. В декабре публичный стенд, исправление завышения и перепроверка на новых сезонах, настоящий Telegram-бот. В январе данные региона и реальные фермеры. В феврале материалы и репетиция. Региональные финалы в феврале и марте, мировой финал в мае в Ханчжоу.");

  /* ===== 12. Closing ===== */
  pres.addSection({ title: "Итог" });
  s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Итог" });
  txt(s, "Совет по поливу, которому можно доверять", { x: M, y: 0.9, w: 12.1, h: 1.0, fontFace: "Cambria", fontSize: 40, bold: true, color: C.background1, objectName: "Итоговый заголовок" });
  txt(s, "потому что мы показываем, как он получен и насколько он точен", { x: M, y: 1.95, w: 12.1, h: 0.6, fontSize: 22, color: C.background2, objectName: "Итоговый подзаголовок" });
  const close = [
    [fa.FaCheckCircle, "Готово", "рабочий прототип и проверка по 20 сезонам на 6 станциях"],
    [fa.FaExclamationTriangle, "Честно", "модель завышает испарение, в Европе не лучше таблицы; исправляем в Build"],
    [fa.FaComments, "Нужно от вас", "критерии оценки и подсказки, где взять данные для региона"],
  ];
  for (let i = 0; i < 3; i++) {
    const y = 3.1 + i * 1.1;
    await iconCircle(s, close[i][0], M, y, 0.75, "Иконка " + close[i][1], C.accent1);
    txt(s, close[i][1], { x: 1.65, y: y + 0.02, w: 2.6, h: 0.7, fontSize: 22, bold: true, color: C.background1, valign: "middle", objectName: "Метка " + close[i][1] });
    txt(s, close[i][2], { x: 4.3, y: y + 0.02, w: 8.4, h: 0.7, fontSize: 18, color: C.background2, valign: "middle", objectName: "Текст " + close[i][1] });
  }
  txt(s, "Вопросы?", { x: M, y: 6.6, w: 6, h: 0.6, fontFace: "Cambria", fontSize: 32, bold: true, color: C.background1, objectName: "Вопросы" });
  note(s, "Итог. Готов рабочий прототип и честная проверка точности. Мы знаем слабые места: завышение испарения и отсутствие данных региона. Это наш план на Build. От жюри нам нужны критерии оценки и подсказки по данным региона. Спасибо, готов к вопросам.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("written", OUT);
}
build().catch((e) => { console.error(e); process.exit(1); });
