"""Turkish translation of the interface."""

TR = {
    "Texel Density": "Texel Yoğunluğu",
    "Set Density": "Yoğunluğu Ayarla",
    "Target": "Hedef",
    "Custom (px/m)": "Özel (px/m)",
    "Texture Size": "Doku Boyutu",
    "Tolerance": "Tolerans",
    "Scale": "Ölçek",
    "Each Island": "Her Ada",
    "Whole Object": "Tüm Obje",
    "Selected Faces Only": "Yalnızca Seçili Yüzler",
    "Measure": "Ölç",
    "Show Colors": "Renkleri Göster",
    "Texture for the target: {n:.0f} px (use {p})": "Hedef için doku: {n:.0f} px ({p} kullan)",
    "Hide Colors": "Renkleri Gizle",
    "Copy from Active": "Aktiften Kopyala",
    "Pack Islands (Keep Density)": "Adaları Paketle (Yoğunluğu Koru)",
    "Average: {a:.0f} px/m ({c:.2f} px/cm)": "Ortalama: {a:.0f} px/m ({c:.2f} px/cm)",
    "Lowest {lo:.0f}, highest {hi:.0f} px/m": "En düşük {lo:.0f}, en yüksek {hi:.0f} px/m",
    "{p:.0f}% of the surface is off target": "Yüzeyin %{p:.0f} kadarı hedef dışı",
    "UV space used: {c:.0f}%": "Kullanılan UV alanı: %{c:.0f}",
    "{n} faces lie outside 0-1": "{n} yüz 0-1 dışında",
    "{n} faces without UV area": "{n} yüzün UV alanı yok",
    "'{name}': {value:.0f} px/m on average.": "'{name}': ortalama {value:.0f} px/m.",
    "None of the selected meshes has a UV map.": "Seçili mesh'lerin hiçbirinde UV haritası yok.",
    "Nothing was scaled: check that the meshes have UV maps and faces.": "Hiçbir şey ölçeklenmedi: mesh'lerde UV haritası ve yüz olduğundan emin ol.",
    "{count} UV islands scaled.": "{count} UV adası ölçeklendi.",
    "{count} objects now have {value:.0f} px/m.": "{count} objenin yoğunluğu artık {value:.0f} px/m.",
}

translations = {"tr_TR": {("*", key): value for key, value in TR.items()}}
