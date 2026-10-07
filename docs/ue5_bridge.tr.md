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

## Adım adım rehber

Bu bölüm Blender'dan Unreal Engine 5'e üç iş akışını anlatır: **statik mesh**, **iskeletli karakter** (modüler parçalarla) ve
**animasyon** (root motion ile). Görsellerdeki sarı numaralar metindeki numaralarla aynıdır.

> **Panel nerede?** 3B görünümde `N` tuşuyla yan çubuğu açın ve **UE5** sekmesine tıklayın (ekran görüntülerinde panel, görüntüleri
> alma yöntemi yüzünden *Item* sekmesinde görünür). **Unreal tarafı:** Unreal Engine'deki adımlar Epic'in FBX içe aktarma akışını
> izler. Bu eklentinin dosyaları Blender'a geri okunarak denetlendi, Unreal'ın kendisinde **denenmedi**.

### A. Statik mesh (kaya, sandık, bina)

1. Mesh'leri seçin. Modifier'lar dışa aktarmada uygulanır, siz bir şey yapmazsınız.
2. Panelin en üstünde **Export Folder**'ı seçin (1). Burada `StaticMeshes`, `SkeletalMeshes` ve `Animations` klasörleri
   oluşur.
3. **UE Name Prefixes** açıkken dosyalar `SM_` ile başlar, **Center at Origin** açıkken her parça (0, 0, 0)'a konarak
   dışa aktarılır; sahnedeki konumları değişmez.
4. **Export Static Meshes**'a basın (7). Her mesh için bir FBX çıkar: `StaticMeshes/SM_Crate.fbx`.
5. **Unreal'da:** *Content Browser*'a FBX'i sürükleyin ya da *Import* deyin. Statik mesh için varsayılan seçenekler yeter. Boyut
   doğru gelir: 1 Blender metresi 100 Unreal santimetresi olur.

### B. İskeletli karakter

![İskelet kontrolü](images/steps/ue5-1-check.png)

1. **Hazırlık.** Armature'a gerçek bir ad verin (`Armature` değil, `Hero`): Unreal bu adı bir kemik sanabilir. Objenin ölçeğini ve
   dönüşünü uygulayın (`Ctrl+A`). Görselde armature'ın ölçeği 2, adı varsayılan ve **iki kök kemiği var** (6: `Hips` ve
   `Prop`).
2. Armature'ı ya da mesh'ini seçin ve **Skeleton** bölümünde **Check Skeleton**'a basın (2). Eklenti **hiçbir şeyi değiştirmeden**
   sorunları listeler (3):
   - *'Armature' has 2 root bones*: Unreal **tam bir** kök kemik ister.
   - *has scale or rotation on the object*: ölçek ve dönüşü uygulayın.
   - *keeps Blender's default name*: armature'ı yeniden adlandırın.
3. Kök kemik sorunu için iki yol var:
   - **Hiçbir şey yapmayın.** **Fix Skeleton on Export** açıkken eklenti dışa aktarma **kopyasında** `root` adlı tek bir kök
     kemik ekler ve diğerlerini ona bağlar. Sahneniz değişmez.
   - Ya da **Add Root Bone**'a basın (4): aynı düzeltmeyi gerçek iskelete uygular.
4. Önemli seçenekler: **Only Deform Bones** (kontrol ve yardımcı kemikleri dışarıda bırakır), **Leaf Bones** (kapalı kalsın; açıksa
   Unreal'da her zincirin ucunda hayalet kemik görünür).
5. **Skeletal Meshes** için seçin: **One File per Mesh** modüler parçalar (pantolon, ceket, ayakkabı) içindir; hepsi aynı iskeleti
   paylaşır ve Unreal'da birbirine oturur. **One File** her şeyi tek FBX'e koyar.
6. **Export Skeletal Meshes**'a basın (5). Çıktı: `SkeletalMeshes/SK_Hero_body.fbx` gibi dosyalar.
7. **Unreal'da:** FBX'i sürükleyin. İlk parçayı içe aktarırken **Skeleton** alanını *None* bırakın; Unreal iskelet asset'ini
   kendisi oluşturur. Sonraki parçalarda **aynı iskelet asset'ini** seçin.

### C. Animasyon ve root motion

Önce Blender'da animasyonlarınızı **action** olarak hazırlayın (örneğin `idle`, `walk`, `run`). Kullanılmayan action'ların
kaydedilmesi için her birine **Fake User** (kalkan simgesi) verin ya da NLA'ya yerleştirin.

![Animasyon ayarları](images/steps/ue5-2-animation.png)

1. Armature'ı seçin. **Animation** bölümünde kaynağı seçin (1):
   - **All Actions**: bu iskeleti canlandıran her action bir dosya olur (önerilen).
   - **NLA Tracks**: her NLA track'i bir dosya olur. **Active Action**: yalnızca şu an atanmış action.
2. **Bake Step**: 1 (her karede anahtar). Tüm kemikler pişirilir.
3. Yürüyen bir animasyonu root motion ile çıkarmak için **Root Motion**'ı açın (2). **Hips Bone** alanına (3) kalça kemiğinin
   adını yazın (`Hips`, `pelvis`, `mixamorig:Hips` ...). Boş bırakırsanız ad `hips`/`pelvis` gibi sözcüklerden tahmin edilir.
4. **Export Animations**'a basın (4). Çıktı: `Animations/A_Hero_walk.fbx`, her action için bir dosya.

**Root motion ne yapar?**

![Root motion öncesi ve sonrası](images/steps/ue5-3-root-motion.png)

- **Önce:** Yürüyüş kalçanın hareketindedir; kök kemik başladığı yerde kalır. Unreal karakteri hareket ettirmek için kök kemiğe
  bakar, bu yüzden karakter animasyonda ilerler ama dünyada yerinde durur.
- **Sonra:** Kalçanın **yatay hareketi** (ileri, yana) her karede kök kemiğe taşınır. Kalçada yalnızca küçük sallanma kalır ve her
  karenin nihai pozu sizin canlandırdığınızla birebir aynıdır. Unreal karakteri kök kemikle ilerletir.
- Dönüş (yaw) çıkarılmaz; kalçada kalır.

Kurallar:

- Kalça ya **tek kök** olmalı (eklenti onun üstüne bir kök kemik ekler) ya da kökün **hemen altında** durmalı. Daha derindeyse
  dışa aktarma bir mesajla durur.
- **NLA Tracks** ile root motion kullanılamaz (track'ler birden çok action'ı harmanlayabilir); mesaj çıkar.

**Unreal'da animasyon:** FBX'i sürükleyin, **Skeleton** olarak daha önce oluşan iskelet asset'ini seçin ve **Import Mesh**'i
kapatın. Root motion için animasyon asset'ini açın, *Asset Details* altında **Enable Root Motion**'ı işaretleyin.

### Doğrulama (Unreal'sız)

Dışa aktarılan dosyayı Blender'a geri alarak kontrol edebilirsiniz (*File > Import > FBX*): tek kök kemik, `_end` adlı hayalet
kemik olmaması, doğru boyut ve animasyon uzunluğu. Eklentinin testi bunu otomatik yapar.

### Sık karşılaşılan sorunlar

| Belirti | Sebep ve çözüm |
|---|---|
| Unreal fazladan bir kök kemik gösteriyor ya da karakter dönük | **Armature Node** değerini *Root* ya da *Limb Node* yapıp tekrar dışa aktarın. Unreal'da denenemeyen tek ayar budur |
| Karakter 100 kat küçük ya da büyük | Blender sahne birim ölçeği 1 olsun, ölçeği iki kez uygulamayın. Dışa aktarma FBX Units Scale kullanır |
| Her zincirin ucunda hayalet kemikler | **Leaf Bones** kapalı olmalı |
| Animasyon oynuyor ama karakter ilerlemiyor | **Root Motion**'ı açıp dışa aktarın, Unreal'da animasyonda **Enable Root Motion**'ı işaretleyin |
| "Root motion needs actions, not NLA tracks" | Kaynağı **All Actions** ya da **Active Action** yapın |
| "Could not find the hips bone" | **Hips Bone** alanına kalça kemiğinin tam adını yazın |
| Action dışa aktarılmadı | Action'a Fake User verin ya da armature'a atayın; boş ya da bu iskeleti canlandırmayan action'lar atlanır |

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
