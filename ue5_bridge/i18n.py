"""Turkish translation of the interface."""
TR = {
    "UE5 Bridge": "UE5 Köprüsü",
    "Skeleton": "İskelet",
    "Animation": "Animasyon",
    "Export Folder": "Dışa Aktarma Klasörü",
    "UE Name Prefixes": "UE Ad Önekleri",
    "Center at Origin": "Merkeze Al",
    "Skeletal Meshes": "İskeletli Mesh'ler",
    "One File per Mesh": "Mesh Başına Bir Dosya",
    "One File": "Tek Dosya",
    "Fix Skeleton on Export": "Dışa Aktarırken İskeleti Düzelt",
    "Root Bone": "Kök Kemik",
    "Only Deform Bones": "Yalnızca Deform Kemikleri",
    "Leaf Bones": "Yaprak Kemikler",
    "Armature Node": "Armature Düğümü",
    "Tangent Space": "Tangent Uzayı",
    "Animations": "Animasyonlar",
    "All Actions": "Tüm Action'lar",
    "NLA Tracks": "NLA Track'leri",
    "Active Action": "Aktif Action",
    "Root Motion": "Root Motion",
    "Hips Bone": "Kalça Kemiği",
    "Bake Step": "Bake Adımı",
    "Check Skeleton": "İskeleti Kontrol Et",
    "Add Root Bone": "Kök Kemik Ekle",
    "Export Static Meshes": "Statik Mesh'leri Dışa Aktar",
    "Export Skeletal Meshes": "İskeletli Mesh'leri Dışa Aktar",
    "Export Animations": "Animasyonları Dışa Aktar",
    "Only the horizontal movement of the hips is moved to the root bone (turning stays on the hips).":
        "Yalnızca kalçanın yatay hareketi kök kemiğe taşınır (dönüş kalçada kalır).",
    "'{name}' has {count} root bones ({roots}): UE5 needs exactly one.":
        "'{name}' için {count} kök kemik var ({roots}): UE5 tam bir tane ister.",
    "'{name}' has no deform bones.": "'{name}' içinde deform kemiği yok.",
    "'{name}' has scale or rotation on the object: apply it (Ctrl+A) before animating.":
        "'{name}' objesinde ölçek ya da dönüş var: animasyondan önce uygula (Ctrl+A).",
    "'{name}' keeps Blender's default name: UE5 can mistake it for a bone.":
        "'{name}' Blender'ın varsayılan adını taşıyor: UE5 bunu kemik sanabilir.",
    "{count} problems found.": "{count} sorun bulundu.",
    "No problems found.": "Sorun bulunamadı.",
    "Nothing to export in the selection.": "Seçimde dışa aktarılacak bir şey yok.",
    "Exported {count} files to {folder}": "{count} dosya {folder} konumuna aktarıldı",
    "Choose an export folder first.": "Önce bir dışa aktarma klasörü seç.",
    "The FBX exporter failed for '{name}'.": "FBX dışa aktarıcı '{name}' için başarısız oldu.",
    "No mesh is skinned to '{name}'.": "'{name}' iskeletine bağlı mesh yok.",
    "'{name}' has no animation to export.": "'{name}' için dışa aktarılacak animasyon yok.",
    "Root motion needs actions, not NLA tracks.": "Root motion için NLA track'i değil action gerekir.",
    "'{hips}' must hang directly under the root bone for root motion.":
        "Root motion için '{hips}' doğrudan kök kemiğin altında olmalı.",
    "Could not find the hips bone: type its name in Hips Bone.":
        "Kalça kemiği bulunamadı: adını Kalça Kemiği alanına yaz.",
}

translations = {"tr_TR": {("*", key): value for key, value in TR.items()}}
