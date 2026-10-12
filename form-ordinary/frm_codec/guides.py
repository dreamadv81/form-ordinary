"""Направляющие края формы: дальние направляющие и их исправление (`normalize_guides`).

Направляющие края — правая (`u4` = 3) и нижняя (`u4` = 4) направляющие страницы формы: координата `u1` и отступ `u7` от края формы,
«край = координата + отступ». У формы платформы отступ правой направляющей 8 (6 при Рамке «Одинарная»; у страницы 0 при закладках «Сверху» — 0), нижней — 8, 19 или от 25 до 37 (нижняя командная панель; чаще всего 33). При смене
размера формы палитрой или мышью платформа двигает такую направляющую вместе с краем: координата += Δ, отступ прежний.

**Дальняя направляющая** — отступ больше `FAR_MARGIN[номер края]` px (правая 20, нижняя 40): позиция не у края формы. Такая получается, если размер формы сменили записью в файл,
оставив координату прежней (платформа при открытии пересчитывает отступ, а не координату). На образце разделителей с дальними направляющими
(472/128 и 470/50 при форме 600×520) окно +200 по ширине дало рост полей +204, горизонтальную прокрутку, и после возврата окна раскладка не
сжалась («залипание»); с направляющими у краёв (592/8 и 512/8) при трёх способах растяжения прокрутки нет, рост равен приросту окна, возврат
точный. У настоящих форм дальние направляющие редки. Предупреждение — `far_words`, исправление — операция
`normalize_guides`.
"""
from . import edit
from .edit.base import EditError

PANEL_GAP = 8        # платформа ставит верхнюю (нижнюю) направляющую в 8 px от командной панели у края: 33 при панели высотой 25
FAR_MARGIN = {3: 20, 4: 40}   # отступ направляющей края больше стольких px — дальняя (правая: у 4 990 форм из 4 993 он не больше 20; нижняя: платформа пишет до 37)
EDGE_MARGIN = 8      # отступ направляющих у края формы платформы
BORDER_MARGIN = 6    # то же при Рамке «Одинарная» (платформа сдвинула 8 → 6)
ORDERS = {3: "правая", 4: "нижняя"}
PANEL_ORDERS = {2: "верхняя", 4: "нижняя"}


def _int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def edge_guides(doc):
    """Направляющие края формы с целым отступом и координатой: `[(индекс, словарь)]`; пусто, если блока нет или он испорчен."""
    try:
        block = edit.layout_block(edit.container(doc), need=False) if isinstance(doc, dict) else None
    except EditError:      # у документа нет контейнера формы: направляющих нет
        return []
    listed = block.get(edit.GUIDES) if isinstance(block, dict) else None
    return [(at, guide) for at, guide in enumerate(listed if isinstance(listed, list) else ())
            if isinstance(guide, dict) and guide.get(edit.GUIDE_ORDER) in ORDERS
            and _int(guide.get(edit.GUIDE_COORD)) and _int(guide.get(edit.GUIDE_OFFSET))]


def far_guides(doc):
    """Дальние направляющие края: `[(страница, номер края, координата, отступ)]`."""
    return [(guide.get(edit.GUIDE_PAGE), guide[edit.GUIDE_ORDER], guide[edit.GUIDE_COORD], guide[edit.GUIDE_OFFSET])
            for _at, guide in edge_guides(doc) if guide[edit.GUIDE_OFFSET] > FAR_MARGIN[guide[edit.GUIDE_ORDER]]]


def far_words(doc):
    """Предупреждение о дальних направляющих края — строки отчёта; пусто, когда их нет."""
    found = far_guides(doc)
    if not found:
        return []
    named = "; ".join(f"{ORDERS[order]} направляющая {'страницы ' + str(page) + ' ' if page else ''}в {coord} (отступ {margin})"
                      for page, order, coord, margin in found)
    return [f"   предупреждение: дальняя направляющая края: позиция не у края формы — {named}; в предприятии раскладка может «залипать» после "
            "растяжения окна (полоса прокрутки, после возврата окна раскладка не сжимается; у направляющих с отступом 8 так не бывает). "
            "Исправляет операция `normalize_guides` (направляющие к краю, элементы не двигаются)"]


def _bars_at_edges(doc):
    """Командные панели родителя-формы, страницы 0, видимые, на всю ширину формы и касающиеся верхнего или нижнего края:
    `{2: [(имя, низ панели)], 4: [(имя, верх панели)]}` (2 — верхняя направляющая, 4 — нижняя) и размер формы `(ширина, высота)`.
    Форма с закладками «Сверху» и документ без размера — пусто: у них направляющие страницы 0 другого рода."""
    from . import anchors
    out = {2: [], 4: []}
    try:
        container = edit.container(doc)
        block = doc["form"]
        width, height = block.get("width"), block.get("height")
        if not (_int(width) and _int(height)) or anchors.tabs_area(doc) is not None:
            return out, None
        items = (container.get(edit.ELEMENTS) or {}).get(edit.ITEMS) or []
    except (EditError, KeyError, AttributeError, TypeError):
        return out, None
    for element in items:
        coords = element.get(edit.COORDS) if isinstance(element, dict) else None
        if element.get("type") != "CommandBar" or not isinstance(coords, dict) or coords.get("visible") is False:
            continue
        if coords.get(edit.PAGE, 0) != 0:
            continue
        x, y, right, bottom = (coords.get(k) for k in (edit.X, edit.Y, edit.WIDTH, edit.HEIGHT))
        if not all(_int(v) for v in (x, y, right, bottom)) or x > 1 or right < width - 1:
            continue
        names = element.get(edit.NAME_BLOCK)
        name = names.get(edit.NAME) if isinstance(names, dict) else None
        if y <= 1 and bottom > y:
            out[2].append((name, bottom))
        if bottom >= height - 1 and bottom > y:
            out[4].append((name, y))
    return out, (width, height)


def panel_guides(doc):
    """Направляющие страницы 0 внутри командной панели у края: `[(номер края, координата, имя панели, граница панели, нужная координата)]`.

    Верхняя направляющая (`u4` = 2) внутри верхней панели, если лежит ниже края формы и выше низа панели; платформа ставит её в `PANEL_GAP`
    под панель (панель 25 → 33). Нижняя (`u4` = 4) — зеркально: ниже верха нижней панели и выше нижнего края; платформа — на `PANEL_GAP` над
    панелью (отступ 33 при панели 25). Направляющая у самого края формы (координата 0 сверху, высота формы снизу) не считается: так платформа
    пишет 134 формы корпуса с нижней и 12 с верхней панелью. Из 4 992 форм корпуса направляющая внутри панели у 9 форм (7 нижних направляющих, 2 верхних).
    """
    bars, size = _bars_at_edges(doc)
    if size is None:
        return []
    found = []
    for _at, guide in _all_guides(doc):
        order, coord = guide.get(edit.GUIDE_ORDER), guide.get(edit.GUIDE_COORD)
        if guide.get(edit.GUIDE_PAGE, 0) != 0 or not _int(coord):
            continue
        if order == 2 and bars[2]:
            name, edge = max(bars[2], key=lambda b: b[1])
            if 0 < coord < edge:
                found.append((2, coord, name, edge, edge + PANEL_GAP))
        if order == 4 and bars[4]:
            name, edge = min(bars[4], key=lambda b: b[1])
            if edge < coord < size[1]:
                found.append((4, coord, name, edge, edge - PANEL_GAP))
    return found


def _all_guides(doc):
    """Все направляющие блока раскладки родителя-формы с целой координатой: `[(индекс, словарь)]`."""
    try:
        block = edit.layout_block(edit.container(doc), need=False) if isinstance(doc, dict) else None
    except EditError:
        return []
    listed = block.get(edit.GUIDES) if isinstance(block, dict) else None
    return [(at, g) for at, g in enumerate(listed if isinstance(listed, list) else ()) if isinstance(g, dict)]


def panel_words(doc):
    """Предупреждение о направляющих внутри панелей у края — строки отчёта; пусто, когда их нет."""
    found = panel_guides(doc)
    if not found:
        return []
    named = "; ".join(f"{'верхняя' if order == 2 else 'нижняя'} направляющая в {coord} внутри панели «{name}» "
                      f"({'до' if order == 2 else 'от'} {edge}), платформа ставит в {want}"
                      for order, coord, name, edge, want in found)
    return ["   предупреждение: направляющая формы внутри командной панели у края — " + named + "; при растяжении окна возможна полоса прокрутки формы "
            "(опыт в предприятии: из четырёх форм с такими направляющими и панелями у краёв три получили полосу прокрутки при каждом растяжении "
            "(у формы с одной верхней панелью — горизонтальную), четвёртая — в одном заходе из двух, и раскладка после возврата окна не вернулась; "
            "та же форма с направляющими 33/H−33 полос не дала, форма без панелей — тоже; размер окна, при котором полоса появится, не выведен: она шла уже "
            "на +45×+23; причина не выяснена, правило выведено из совпадения). Исправляет операция `normalize_guides` (направляющие к панелям, элементы не двигаются)"]


def fit_panel(doc, element):
    """Для `add_element`: поставленная командная панель родителя-формы у края стала поверх направляющей страницы 0 — направляющая уходит на
    `PANEL_GAP` от панели, как у платформы. Направляющие вне панели не трогаются. Возвращает слова операции или `""`."""
    names = element.get(edit.NAME_BLOCK)
    name = names.get(edit.NAME) if isinstance(names, dict) else None
    moved = []
    for order, coord, who, _edge, want in panel_guides(doc):
        if who != name:
            continue
        for _at, guide in _all_guides(doc):
            if guide.get(edit.GUIDE_ORDER) == order and guide.get(edit.GUIDE_PAGE, 0) == 0 and guide.get(edit.GUIDE_COORD) == coord:
                height = doc["form"]["height"]
                guide[edit.GUIDE_COORD] = want
                if order == 4:
                    guide[edit.GUIDE_OFFSET] = height - want
                moved.append(f"{'верхняя' if order == 2 else 'нижняя'} направляющая {coord} → {want}")
                break
    if not moved:
        return ""
    return ("направляющие формы стояли внутри панели и перенесены от неё на 8 px, как ставит платформа (" + "; ".join(moved)
            + "): иначе при растяжении окна форма получала полосу прокрутки (проверено одним опытом в предприятии, вне него не проверялось)")


def normalize_guides(doc, margin=None, unverified=False):
    """Дальние направляющие края — к краю формы: край (координата + отступ) прежний, отступ — `margin` (умолчание 8, при Рамке 6), координата —
    край минус отступ. Направляющие с отступом не больше `FAR_MARGIN` своего края не трогаются, элементы и привязки тоже.

    Вторая часть — **направляющие внутри командных панелей у краёв** (`panel_guides`): верхняя уходит на `PANEL_GAP` под верхнюю панель, нижняя —
    на `PANEL_GAP` над нижней (панель 25 → 33 и H−33, как у платформы); в опыте в предприятии это сняло полосу прокрутки при растяжении окна.

    `margin` — целое от 0 до 20; большее число — это снова дальняя правая направляющая, под `unverified`. Возвращает отчёт.
    """
    if margin is None:
        margin = BORDER_MARGIN if _border(doc) else EDGE_MARGIN
    elif not _int(margin) or margin < 0:
        raise EditError(f"margin: целое неотрицательное число (отступ направляющей от края формы), а пришло {margin!r}")
    elif margin > FAR_MARGIN[3] and not unverified:
        raise EditError(f"margin {margin}: отступ больше {FAR_MARGIN[3]} — это снова дальняя направляющая (`far_words`); платформа пишет 8 "
                        f"(6 при Рамке). Позвать всё же можно — unverified=True")
    moved = []
    for _at, guide in edge_guides(doc):
        was = guide[edit.GUIDE_OFFSET]
        if was <= FAR_MARGIN[guide[edit.GUIDE_ORDER]]:
            continue
        edge = guide[edit.GUIDE_COORD] + was
        moved.append(f"{ORDERS[guide[edit.GUIDE_ORDER]]} страницы {guide.get(edit.GUIDE_PAGE)}: {guide[edit.GUIDE_COORD]}/{was} → {edge - margin}/{margin}")
        guide[edit.GUIDE_COORD] = edge - margin
        guide[edit.GUIDE_OFFSET] = margin
    panel = []
    for order, coord, name, _edge, want in panel_guides(doc):
        for _at, guide in _all_guides(doc):
            if guide.get(edit.GUIDE_ORDER) == order and guide.get(edit.GUIDE_PAGE, 0) == 0 and guide.get(edit.GUIDE_COORD) == coord:
                guide[edit.GUIDE_COORD] = want
                if order == 4:
                    guide[edit.GUIDE_OFFSET] = doc["form"]["height"] - want
                panel.append(f"{PANEL_ORDERS[order]} направляющая {coord} → {want} (панель «{name}»)")
                break
    if not moved and not panel:
        return (f"normalize_guides: дальних направляющих края (отступ правой больше {FAR_MARGIN[3]}, нижней больше {FAR_MARGIN[4]}) нет, форма не изменена; "
                "направляющих внутри командных панелей у краёв тоже нет")
    said = []
    if moved:
        said.append(f"normalize_guides: направляющих края перенесено к краю формы {len(moved)} (край прежний, отступ {margin}): " + "; ".join(moved)
                    + "; элементы и привязки не тронуты. Форма с направляющими у краёв в предприятии проверена: поля растут ровно на прирост окна, "
                      "после возврата окна раскладка прежняя"
                    + ("; отступ не 8 (в том числе 6 при Рамке) в предприятии не проверялся" if margin != EDGE_MARGIN else ""))
    if panel:
        said.append(("normalize_guides: " if not moved else "") + f"направляющих внутри панелей у краёв перенесено от панели на {PANEL_GAP} px, как ставит платформа, {len(panel)}: "
                    + "; ".join(panel) + "; элементы и привязки не тронуты. Форма с направляющими 33/H−33 при растяжении окна полос не дала, с направляющими "
                      "внутри панелей — давала (один опыт в предприятии)")
    return "; ".join(said)


def _border(doc):
    """Рамка формы не «Нет»: `border_type` блока рамки; нечитаемое — без рамки."""
    from .edit.pages import _form_border_type, FORM_NO_BORDER
    value = _form_border_type(doc)
    return value not in (None, FORM_NO_BORDER)
