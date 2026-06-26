# Design System: RealtyScope Hybrid Analytics Workstation
**Project IDs:** Direction A - Structured Dashboard `11077663518584587281`; RealtyScope Analytics Workstation Project B `5104128913779687`

## 1. Visual Theme & Atmosphere
RealtyScope uses an institutional real estate intelligence aesthetic: dense, precise, and operational. Direction A contributes the readable 260px expanded sidebar, clear dashboard hierarchy, and structured dashboard rhythm. Project B contributes the compact workstation rail, analytical panes, crisp borders, and darker Moscow intelligence mood.

The unified UI should feel like a professional financial and GIS workstation for Moscow apartment analysis. It must avoid decorative real estate luxury styling, fabricated demo values, marketing copy, and visible implementation terminology. Every panel should either navigate, filter, calculate, inspect real listings, or report service health.

## 2. Color Palette & Roles
- **Deep Workstation Canvas (#111418):** Default dark background for the app shell.
- **Compact Sidebar Charcoal (#0B0E12):** Persistent navigation surface.
- **Analytical Surface (#191C20):** Primary cards, tables, forms, and panes.
- **Raised Surface (#272A2E):** Hover states, selected controls, and active analytical panes.
- **Precision Border (#3D4947):** Default 1px outlines and dividers.
- **Strong Border (#879391):** Focus, selected, or elevated elements.
- **Primary Teal (#6BD8CB):** Active navigation, primary actions, live status, selected chart series.
- **Teal Deep Container (#00302B):** Dark supporting fill for primary actions and active badges.
- **Secondary Indigo (#C3C0FF):** Secondary chart emphasis and comparative analytics.
- **System Success (#38D39F):** Available service and valid data states.
- **Warning Amber (#F59E0B):** Partial or delayed system states.
- **Soft Error (#FFB4AB):** Unavailable services and warning rows.
- **Light Canvas (#F8FAFC):** Light mode app background.
- **Light Surface (#FFFFFF):** Light mode cards and forms.
- **Light Border (#CBD5E1):** Light mode dividers and table outlines.

## 3. Typography Rules
Use **Inter** for the entire application because it is legible in dense tables and supports Cyrillic well. Use **Manrope** only for page titles and large dashboard headings when extra product presence is needed.

All numeric values, prices, coordinates, and table cells must use tabular figures. Russian UI labels should be professional and user-facing: use "Оценка стоимости", "Тепловая карта", "Сравнение сегментов", "Данные объявлений", and "Мониторинг". Do not show raw field names such as `model_version`, `feature_version`, or `caveat` in the interface.

## 4. Component Stylings
* **Sidebar:** Default expanded width is about 260px with logo text and labels. Collapsed mode becomes a compact rail around 88px with symbolic labels. The RealtyScope logo button always returns to the dashboard.
* **Navigation Items:** Active state uses a subtle teal container, a left accent stroke, and teal text. Hover uses raised charcoal and quick color transitions.
* **Buttons:** Primary actions are solid teal with 8px radius, subtle hover brightness, and a small active scale animation. Secondary actions use surface fills and 1px borders.
* **Cards/Containers:** Cards use flat tonal layers, 8px radius, 1px borders, and no decorative shadows. Hover only shifts the border toward teal.
* **Inputs/Forms:** Inputs sit on inset surfaces with precision borders. Focus states use teal borders and no heavy glow.
* **Tables:** Dense analytical tables with tabular numbers, compact row height, and clear Russian headers.
* **Maps/Charts:** Maps and charts use real stored listing data only. Heatmap and point colors should stay in the teal, cyan, indigo, amber, and error scale.
* **Theme Switcher:** Located in the sidebar, with clear Russian light/dark behavior. It must change the entire semantic palette, not just invert text.

## 5. Layout Principles
The app uses a fixed-fluid hybrid layout. Desktop starts with an expanded sidebar and a sticky top bar. Content is organized into analytical panes with 12-column behavior expressed through Streamlit columns. Mobile and narrow screens should let the sidebar overlay while the content becomes single-column.

Spacing follows a 4px baseline. Dashboard panels use 16px internal padding, 16px gutters, and compact headings. Avoid nested decorative cards and avoid hero or landing-page composition. The first screen is always the working dashboard.

## 6. Interaction Rules
Every visible control should do something: navigation changes pages, logo returns home, theme switch changes palette, sidebar toggle changes density, form submission calls the prediction endpoint, report buttons download text, and map/filter controls alter the view or state.

Page changes should feel animated through a short fade-and-slide transition. Buttons should use hover and active feedback. Do not include inert placeholder buttons copied from Stitch.
