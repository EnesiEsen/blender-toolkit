# UE5 Bridge

Blender'dan Unreal Engine 5'e temiz FBX dışa aktarma: statik mesh'ler, tek iskeleti paylaşan modüler iskeletli mesh'ler,
animasyonlar (action ya da NLA track başına bir dosya) ve isteğe bağlı root motion. Her dışa aktarma objelerinin geçici
kopyaları üzerinde çalışır; sahnende hiçbir şey taşınmaz, uygulanmaz ya da yeniden adlandırılmaz.

[English](ue5_bridge.md) · [Genel bakışa dön](../README.tr.md)

![UE5 Bridge paneli](images/ue5_bridge.png)

> **Durum.** Dışa aktarılan dosyalar Blender'a geri içe aktarılarak denetlendi (kemik hiyerarşisi, boyutlar, animasyon
> uzunluğu, root motion). Eklenti **Unreal Engine'in içinde test edilmedi**, çünkü elde UE yoktu. Ayarlar Epic'in FBX
> rehberini izler; Unreal'da deneme gerektirebilecek tek ayar **Armature Node**'dur (Sorun giderme bölümüne bak).

Panel, yan çubuktaki **UE5** sekmesindedir.

## Dışa aktarmalar neyi kullanır

Bu FBX ayarları bilerek sabittir; Unreal'a doğru boyutta ve yönde girenler bunlardır: Apply Scalings = *FBX Units Scale*
(1 Blender metresi 100 Unreal santimetresi olur), varsayılan eksenler (-Z ileri, Y yukarı), yüz yumuşatma, tangent
uzayı (isteğe bağlı), leaf kemik yok, birincil kemik ekseni Y. Dosya adları Unreal için güvenli yapılır: ASCII harf,
rakam ve alt çizgi; Blender'ın `.001` eki silinir.

## Statik mesh'ler

1. Mesh'leri seç.
2. **Export Folder**'ı ayarla (içinde `StaticMeshes` klasörü oluşur).
3. **Export Static Meshes**'a bas. Mesh başına bir FBX; modifier'lar uygulanır, dönüş ve ölçek pişirilir.

| Seçenek | Ne yapar |
|---|---|
| UE Name Prefixes | Ad zaten öyle başlamıyorsa dosyaları `SM_` (statik), `SK_` (iskeletli), `A_` (animasyon) olarak adlandırır. |
| Center at Origin | Her parçayı sahnede nerede durursa dursun (0, 0, 0)'a koyarak aktarır. |

Skin'li mesh'ler burada atlanır; onları iskeletli mesh olarak aktar.

## İskeletli mesh'ler

Armature'ı (ya da mesh'lerini) seç ve **Export Skeletal Meshes**'a bas. Dosyalar `SkeletalMeshes` klasörüne gider.

| Seçenek | Ne yapar |
|---|---|
| Skeletal Meshes: One File per Mesh | Modüler parçalar (pantolon, ceket, ayakkabı) tek tek aktarılır, hepsi aynı iskeleti paylaşır; böylece Unreal'da birbirine oturur. |
| Skeletal Meshes: One File | İskelet ve tüm mesh'leri tek FBX'te. |
| Fix Skeleton on Export | Unreal tam bir kök kemik ister. İskelette birden çok varsa, onların üstüne **yalnızca dışa aktarma kopyasında** bir kök kemik (**Root Bone** adıyla, varsayılan `root`) eklenir. |
| Only Deform Bones | Kontrol ve yardımcı kemikleri dosyanın dışında bırakır. |
| Leaf Bones | Varsayılan kapalı. Açıkken Blender her zincire fazladan bir uç kemik ekler; Unreal bunları hayalet kemik olarak gösterir. |
| Armature Node | Armature objesinin kendisinin nasıl yazılacağı (*Null*, *Root*, *Limb Node*). |
| Tangent Space | Tangent'leri yazar. |

**Check Skeleton** hiçbir şeyi değiştirmeden sorunları listeler: birden fazla kök kemik, deform kemiği yok, armature
objesinde ölçek ya da dönüş ve varsayılan `Armature` adı (Unreal bunu kemik sanabilir). **Add Root Bone** kök sorununu
gerçek iskelette de düzeltir; .blend dosyasında da düzelsin istersen.

## Animasyonlar

Armature'ı seç ve **Export Animations**'a bas. Dosyalar `Animations` klasörüne, `A_<armature>_<animasyon>.fbx`
adıyla gider.

| Seçenek | Ne yapar |
|---|---|
| Animations: All Actions | Bu iskeleti canlandıran her action, birer dosya. |
| Animations: NLA Tracks | Her NLA track'i kendi dosyası olur, track'in adını taşır. |
| Animations: Active Action | Yalnızca şu an armature'a atanmış action. |
| Bake Step | Pişirilen anahtarlar arası kare sayısı (1 = her kare). Tüm kemikler pişirilir. |
| Root Motion | Aşağıya bak. |
| Hips Bone | Root motion için kalça kemiğinin adı. Boş bırakırsan addan tahmin edilir (hips, pelvis ...). |

### Root motion

Unreal bir karakteri kök kemikle sürer (Root Motion, Motion Matching). **Root Motion** açıkken kalçanın yatay hareketi
(ileri, yana) her karede kök kemiğe taşınır. Kalçada yalnızca artan hareket kalır (sallanma, salınım) ve her karenin
nihai pozu senin canlandırdığınla birebir aynı kalır. Dönüş çıkarılmaz: kalçada kalır.

- Kalça tek kök ise, onun üstüne yeni bir kök kemik eklenir (dışa aktarma kopyasında).
- Kalça hiyerarşide kökün hemen altından daha derindeyse dışa aktarma bir mesajla durur.
- Root motion action'larla çalışır. **NLA Tracks** ile bir mesajla reddedilir, çünkü track'ler birden çok action'ı
  harmanlayabilir.

## Tipik iş akışı

1. İskeleti bir kez kur, obje ölçeğini ve dönüşünü uygula (`Ctrl+A`), armature'a gerçek bir ad ver (`Armature` değil,
   `Hero`).
2. **Check Skeleton**.
3. **Export Skeletal Meshes**'ı bir kez çalıştır: Unreal'a aktar ve iskelet asset'ini oluşturmasına izin ver.
4. **Export Animations**; Unreal'a aktarırken o mevcut iskeleti seç, böylece tüm animasyonlar onu paylaşır.

## Sorun giderme

- **Unreal fazladan kök kemik gösteriyor ya da karakter dönük.** Başka bir **Armature Node** değeri dene (*Root* ya da
  *Limb Node*). Unreal'da test edilemeyen tek ayar buydu.
- **Karakter 100 kat küçük ya da büyük.** Blender sahne birim ölçeğinin 1 olduğundan ve ölçeği iki kez uygulamadığından
  emin ol. Dışa aktarmalar FBX Units Scale kullanır.
- **Her zincirin ucunda hayalet kemikler.** **Leaf Bones**'u kapalı tut.
- **Animasyon oynuyor ama karakter dünyada ilerlemiyor.** **Root Motion**'ı aç ve Unreal'da animasyon asset'inde root
  motion'ı etkinleştir.

## Sınırlar

- Unreal Engine'in kendisinde doğrulanmadı (durum notuna bak).
- Root motion yalnızca öteleme çıkarır, yaw (dönüş) çıkarmaz.
- Yalnızca FBX yolu kapsanır. Alembic, USD ve Unreal Python API'si kullanılmaz.
