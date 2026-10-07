# FiveM Toolkit

Düz Blender mesh'lerini daha az tıklamayla FiveM varlığına çevirir: FiveM varlıklarını bozan şeyleri bulup güvenli
olanları düzelten bir **Doktor**, **Prop** üretici (drawable, collision, LOD, archetype, DDS doku), **MLO / İç Mekân**
üretici ve **Ped** ağırlık araçları. [Sollumz](https://docs.sollumz.org) üzerine kuruludur; GTA V dosya dönüşümünü
Sollumz yapar, bu eklenti sahneni ona hazırlar ve onu yönetir.

[English](fivem_toolkit.md) · [Genel bakışa dön](../README.tr.md)

![FiveM Toolkit paneli](images/fivem_toolkit.png)

## Gereksinimler

- Blender 5.0 – 5.2.
- **Sollumz** kurulu ve etkin olmalı. Yoksa panelde kırmızı bir uyarı görünür. Sollumz geliştirme sürümleriyle test
  edildi: 2.8.0 (Blender 5.0) ve 2.8.3 (Blender 5.2).

Panel, yan çubuktaki **FiveM** sekmesindedir. Ne ürettiğini **Prop**, **MLO / Interior** ya da **Ped / Clothing** ile
seç. **Doctor** ve **Export** alt panelleri ortaktır.

## Adım adım rehber

Bu bölüm üç iş akışını örneklerle anlatır: **prop**, **MLO / iç mekân** ve **ped / kıyafet**. Görsellerdeki sarı numaralar
metindeki numaralarla aynıdır. Görseller Blender 5.2 ve Sollumz 2.8.3 ile alınmıştır.

> **Önce Sollumz'u etkinleştirin.** *Edit > Preferences > Add-ons* içinde `Sollumz` yazın ve kutusunu işaretleyin. Etkin
> değilse FiveM paneli kırmızı bir uyarı gösterir. **Panel nerede?** 3B görünümde `N` tuşuyla yan çubuğu açın ve **FiveM**
> sekmesine tıklayın (ekran görüntülerinde panel, görüntüleri alma yöntemi yüzünden *Item* sekmesinde görünür).

### A. İlk prop'unuz: sandıktan oyuna

**1. Modeli hazırlayın.**

- **Gerçek boyutta** modelleyin: 1 Blender birimi = 1 metre. Bir sandık yaklaşık 1 metredir.
- **Orijin** (nesnenin sarı noktası) oyundaki dönme ve yerleşme noktasıdır; prop'un tabanının ortasına koyun.
- Materyalde **Principled BSDF**'in *Base Color* girişine bir **Image Texture** bağlayın. PNG ve JPG olabilir, DDS'e eklenti çevirir.

**2. Doktor ile kontrol edin ve düzeltin.**

![Doktor: bozuk bir sandık](images/steps/fivem-1-doctor.png)

1. Mesh'i seçin, **FiveM** sekmesinde **Prop** düğmesine tıklayın (1).
2. **Check Assets**'e basın (2). Burada sandığın adı `My Crate.001`, ölçeği uygulanmamış, üstünde Bevel modifier'ı var, UV'si
   ve materyali yok. Her sorun düz cümleyle listelenir.
3. Güvenli olanların hepsini **Fix All** ile (3), tek tek **Fix** ile (4) düzeltin. Ad `my_crate` olur, ölçek ve modifier
   uygulanır, kutu izdüşümlü bir UV ve varsayılan bir materyal eklenir.
4. Düzeltilemeyen sorunlar (eksik doku dosyası, aşırı üçgen, boş mesh) listede kalır; onları kendiniz çözün.

**3. Prop'u oluşturun.**

![Prop'un oluşturulmuş hâli ve hiyerarşisi](images/steps/fivem-2-prop.png)

1. Aşağıdaki ayarlara bakın ve **Build Props**'a basın (görselde 5'in yeri; düğme, siz zaten oluşturulmuş prop'u seçtiğinizde gri olur):

| Ayar | Önerilen | Ne yapar |
|---|---|---|
| Collision (3) | *Simplified Copy* | Düşük poligonlu çarpışma. Taş ve kaya için *Convex Hull*, içinde yürünecek yapılar için *Exact Mesh* |
| Collision Triangles | 300 | Basit prop için yeterli |
| Generate LODs (4) | Açık | Uzakta daha az üçgenli sürümler |
| LOD Strength / LOD Distance Scale | Balanced / 1.00 | Büyük prop'larda mesafe ölçeğini artırın |
| Create YTYP Archetype (5) | Açık | Oyunun prop'u tanıması için gerekli |
| Convert Textures to DDS (6) | Açık | FiveM DDS ister |
| Fix Problems First | Açık | Doktor'un güvenli düzeltmelerini önce yapar |

2. Sonuç sağdaki Outliner'da görünür: **1** `barrel.col` (prop'un içine gömülü çarpışma), **2** `barrel.model` (görünen mesh,
   LOD'larıyla). En üstteki `barrel` Sollumz'un **drawable**'ıdır. Materyal Sollumz shader'ına çevrilmiştir.
3. Doktor'u tekrar çalıştırın: temiz çıkmalı.

**4. Dışa aktarın.**

1. Aynı panelin **Export** bölümünde (7) **Resource Name** (ör. `my_props`) ve **Output Folder** girin. **Format**:
   *FiveM (binary)*.
2. **Export Resource**'a basın. Çıkan klasör:

```
my_props/
  fxmanifest.lua        kaynağı FiveM'e tanıtır
  stream/
    barrel.ydr          model, LOD'lar, gömülü çarpışma ve dokular
    my_props.ytyp       prop'un tanımı (archetype)
```

**5. Oyunda deneyin.**

1. `my_props` klasörünü sunucunuzun `resources` klasörüne kopyalayın, `server.cfg` dosyasına `ensure my_props` ekleyin.
2. Prop'un oyundaki adı küçük harfli varlık adıdır (`barrel`). Bir betikle çağırmak için örnek:

```lua
local model = joaat('barrel')
RequestModel(model)
while not HasModelLoaded(model) do Wait(0) end
local prop = CreateObject(model, coords.x, coords.y, coords.z, true, true, false)
```

> Bu çıktı Sollumz üzerinden dışa aktarılıp geri okunarak denetlendi; ilk varlığınızı **oyunda da deneyin**.

### B. MLO / iç mekân

MLO'da yapı, **Outliner'daki koleksiyon düzeniyle** tarif edilir. Eklenti bu düzenden odaları, portalları ve çarpışmayı kurar.

![MLO şablonu ve koleksiyon yapısı](images/steps/fivem-3-mlo.png)

1. **MLO / Interior** sekmesine geçin ve **Create Interior Template**'e basın (4). `my_interior` koleksiyonu oluşur:
   - **1** `room.hall` ve `room.kitchen`: her oda için bir alt koleksiyon. Yanındaki kutular yer tutucudur (`hall_shell`).
   - **2** `portal.hall.kitchen`: iki odayı bağlayan açıklık. **3** `portal.limbo.hall`: dış mekândan içeri giriş.
2. **Odaları kendi modelinizle doldurun.** Yer tutucu kutuları silin, her odanın mesh'lerini `room.<ad>` koleksiyonuna taşıyın.
   Yeni oda için yeni bir `room.<ad>` alt koleksiyonu açın. Adlarda küçük harf, rakam ve alt çizgi kullanın.
3. **Portalları yerleştirin.** Portal, kapı ya da pencere açıklığına konan **tek bir quad**'dır (4 vertex, 1 yüz). Adı
   `portal.<odaA>.<odaB>` olmalı; `limbo` dış mekândır. En az bir portalın bir ucu `limbo` olmalı (giriş).
4. Outliner'da **`my_interior` koleksiyonuna tıklayarak** seçin; eklenti bu koleksiyonu işler.
5. **Check Interior**'a basın (5). Hatalar listelenir: portal adı yanlış, olmayan bir odayı adlandıran portal, giriş yok, bir
   obje iki odada, limbo'da 12'den fazla obje (GTA en fazla 12'ye izin verir).
6. **Build Interior**'a basın (6). Oda mesh'leri prop'a çevrilir, iç mekân çarpışması kurulur (*Interior Collision* ve
   *Triangles per Mesh*) ve MLO archetype'ı oda, portal ve objelerle doldurulur.
7. **Export Resource** ile dışa aktarın. Oda mesh'i başına bir `.ydr`, iç mekân çarpışması için bir `.ybn` ve bir `.ytyp` çıkar.

> **Haritaya yerleştirme:** Bu eklenti harita yerleşimi (`.ymap`) yazmaz. MLO'yu haritada görmek için CodeWalker'da bir `.ymap`
> oluşturup `.ytyp` içindeki MLO archetype'ını yerleştirmeniz gerekir. Portal yönü ters görünürse portal adındaki iki oda adını
> yer değiştirin.

### C. Ped / kıyafet: ağırlıkları GTA kemiklerine taşıma

Bu iş akışı, başka bir rig'e (Mixamo, Rigify ...) ağırlıklanmış bir kıyafet ya da karakter mesh'inin vertex group'larını **GTA V
ped iskeletinin kemik adlarına** çevirir; hiçbir ağırlık kaybolmaz.

![Ped doktoru](images/steps/fivem-4-ped.png)

1. **GTA iskeletini hazırlayın.** Sollumz'un içe aktarma menüsüyle (*File > Import*) bir ped YFT'sini içe aktarın. Gelen armature'ı
   **GTA Skeleton** alanına verin (1).
2. Rig'li mesh'leri seçin, **Ped / Clothing** sekmesine geçin ve **Check Assets**'e basın (4). Görselde mesh'in modifier'ı
   uygulanmamış, boş materyal yuvası ve 2 boş vertex group'u var ve **5 vertex group'un adı GTA kemiği değil** (6). Vertex
   group'lar Properties editöründe (5) görünür: `mixamorig:Hips`, `mixamorig:LeftUpLeg` ...
3. **Retarget Weights**'e basın (3). Eklenti adlardan eşleşmeyi tahmin eder (sol/sağ, omurga, parmaklar). GTA'da karşılığı
   olmayan grup **var olan en yakın üst kemiğe birleştirilir**. **Keep Weight Backup** açıkken her mesh'in gizli bir yedeği
   tutulur.
4. Tahmin edemediği adlar için **Create Mapping Sheet**'e basın (2). `fk_bone_map` adlı bir metin bloğu açılır; eşleşmeyen
   grupları listeler. Her satırı `kaynak kemik = GTA kemiği` biçiminde doldurun, örneğin:

```
mixamorig:LeftUpLeg = SKEL_L_Thigh
mixamorig:RightUpLeg = SKEL_R_Thigh
```

   Sonra **Retarget Weights**'i yeniden çalıştırın; sizin satırlarınız tahminlerin yerine geçer.
5. **Check Assets**'i tekrarlayın: "GTA kemiği değil" uyarısı kalkmalı. Vertex başına **en fazla 4 kemik etkisi** olmalı
   (GTA vertex formatı 4 tutar); fazlası Doktor'da uyarı olarak görünür.

> Ped bileşen dosyalarının (`.ydd`, `.ytd`, kıyafet `.ymt` metaverisi) hazırlanması Sollumz'un kendi araçlarıyla yapılır; bu eklenti
> ağırlıkları ve adları hazırlar. `.ymt` dosyalarını yazmaz.

### Sık karşılaşılan sorunlar

| Belirti | Sebep ve çözüm |
|---|---|
| "Sollumz is not installed or not enabled" | *Preferences > Add-ons* içinde Sollumz'u etkinleştirin ve Blender'ı yeniden başlatın |
| **Build Props** gri | Bir **mesh** seçili olmalı (prop'un kendisi değil, ondan önceki mesh) ve Object Mode'da olmalısınız |
| "Fix these first: ..." | Düzeltilemeyen bir hata var (ör. eksik doku dosyası). Önce onu çözün |
| LOD oluşmuyor | Mesh çok az üçgenli (ör. bir kutu). Çok küçük mesh'lere LOD verilmez, bu normaldir |
| Prop oyunda çok büyük ya da küçük | Ölçek: 1 Blender birimi = 1 metre. Modeli gerçek boyuta getirip Doktor'dan ölçeği uygulatın |
| Oyunda görünmüyor | `fxmanifest.lua` ve `stream/` yerinde mi, `ensure` yazıldı mı, `.ytyp` listelendi mi kontrol edin; sunucu konsolundaki hatalara bakın |
| Doku oyunda yok | Dokular `.ydr` içine gömülüdür. **Convert Textures to DDS** açık olsun ve doku boyutu **Max Texture Size**'ı aşmasın |

## Doktor: kontrol et ve düzelt

**Check Assets**'e bas (objeleri seç; hiçbir şey seçili değilse sahne taranır). Her sorun düz cümleyle ve bir **Fix**
düğmesiyle listelenir, ya da **Fix All**'a bas.

| Sorun | Otomatik düzelir mi? | Anlamı |
|---|---|---|
| Geçersiz ya da çift varlık adı | Evet | FiveM varlık adları küçük harf, rakam ve alt çizgiden oluşmalı ve benzersiz olmalı. |
| Uygulanmamış ölçek ya da dönüş | Evet | Prop oyunda doğru boyda olsun diye transform uygulanır. |
| Mesh üzerinde modifier kalmış | Evet | Dönüştürmeden önce uygulanır. |
| UV haritası yok | Evet | Basit bir kutu izdüşümlü UV haritası üretilir. İyi sonuç için UV'yi kendin aç. |
| Materyal yok / kullanılmayan materyal yuvası | Evet | Varsayılan materyal (`fk_default`) eklenir, kullanılmayan yuvalar silinir. |
| Doku çok büyük (**Max Texture Size** üstü, 512 – 4096) | Evet | Doku küçültülür. |
| Doku DDS değil | Evet | Kenarları 2'nin kuvveti olacak şekilde DDS'e çevrilir, **Max Texture Size**'ı aşmaz. Aşağıya bak. |
| Doku dosyası yok | Hayır | Dokuyu yeniden bağla ya da kaldır. |
| **Triangle Warning**'den fazla üçgen (varsayılan 100.000) | Hayır | Mesh'i azalt, örneğin Retopo Kit ile. |
| Boş mesh | Hayır | Sil. |

## Prop

Mesh'leri seç ve **Build Props**'a bas. Her obje için (**One Prop per Object** kapalıysa hepsi birlikte):

1. Önce Doktor'un güvenli düzeltmeleri çalışır (**Fix Problems First**).
2. Mesh bir Sollumz drawable'ı olur ve materyaller dönüştürülür.
3. **Collision**: *Simplified Copy* (düşük poligonlu kopya, varsayılan, hedef **Collision Triangles**), *Convex Hull*,
   *Exact Mesh* ya da *None*.
4. **Generate LODs**: medium, low ve very-low sürümler. **LOD Strength**: *Balanced* (üçgenlerin %50 / 25 / 10'u),
   *Aggressive* (%35 / 12 / 4) ya da *Gentle* (%70 / 45 / 25). Neredeyse hiç kazanç sağlamayacak seviyeler atlanır,
   çok küçük mesh'lere LOD verilmez. **LOD Distance Scale**, prop'un boyundan hesaplanan mesafeleri çarpar.
5. **Create YTYP Archetype**: her prop için doğru sınırlar ve LOD mesafeleriyle bir Sollumz archetype'ı.
6. **Convert Textures to DDS**: FiveM DDS ister (mipmap'li DXT1 ya da DXT5). Eklentinin kendi kodlayıcısı vardır ve alfa
   kanalı varsa korur.

Sonra **Export**'u aç: **Resource Name** ve **Output Folder**'ı gir, **FiveM (binary)** (`.ydr`, `.ybn`, `.ytyp`,
`.ytd`, `stream/` için hazır) ya da **CodeWalker XML** seç ve **Export Resource**'a bas. Bir `stream` klasörü ve `.ytyp`
dosyalarını zaten listeleyen bir `fxmanifest.lua` içeren kaynak klasörü oluşur. **Selected Only** yalnızca seçimi
aktarır.

## MLO / İç mekân

İç mekânlar, tek bir koleksiyonun outliner yapısıyla tarif edilir:

```
my_interior                  <- bu koleksiyonu seç
  room.hall                  <- her oda için bir alt koleksiyon, mesh'leriyle
  room.kitchen
  portal.hall.kitchen        <- iki odayı birleştiren quad (açıklık)
  portal.limbo.hall          <- limbo = dış mekân; bu giriş kapısı
```

1. **Create Interior Template** bir başlangıç düzeni ekler (iki oda, aralarında portal, bir giriş). Kutuları kendi
   mesh'lerinle değiştir.
2. **Check Interior** oda ve portallardaki hataları listeler (ör. olmayan odayı adlandıran portal, ya da limbo'da çok
   fazla obje: GTA en fazla 12'ye izin verir).
3. **Build Interior** oda mesh'lerini propa çevirir, iç mekân collision'ını kurar (**Interior Collision**: **Triangles
   per Mesh** hedefli basit kopya ya da tam mesh) ve MLO archetype'ını oda, portal ve entity'lerle doldurur.
   **Generate LODs**, **Convert Textures to DDS** ve **Fix Problems First** burada da geçerlidir.
4. Proplardaki gibi **Export Resource** ile dışa aktar.

## Ped / Kıyafet

Rig'li karakterler ve kıyafet mesh'leri için.

1. Rig'li mesh'leri seç. **GTA Skeleton**'a bir GTA dosyasından içe aktardığın ped iskeletini ver (Sollumz YFT içe
   aktarma).
2. **Check Assets** ağırlık sorunlarını listeler: armature yok, ağırlıksız vertex, vertex başına 4'ten fazla kemik etkisi
   (GTA vertex formatı 4 tutar), toplamı 1 etmeyen ağırlıklar, boş gruplar ve hiçbir GTA kemiğine uymayan gruplar.
3. **Retarget Weights** vertex group'ları GTA V kemiklerine göre yeniden adlandırır ve birleştirir. Eşleşmeyi adlardan
   tahmin eder (Mixamo, Rigify ve genel rig'ler: sol/sağ, omurga, parmaklar ...). GTA karşılığı olmayan gruplar **var
   olan en yakın üst kemiğe birleştirilir**, yani hiçbir ağırlık kaybolmaz. **Keep Weight Backup** açıkken her mesh'in
   gizli bir yedeği tutulur.
4. Eklentinin tahmin edemediği adlar için **Create Mapping Sheet**'e bas: eşleşmeyen grupları listeleyen bir metin
   bloğu oluşturur. `kaynak kemik = GTA kemiği` satırlarını doldur ve **Retarget Weights**'i yeniden çalıştır; senin
   satırların tahminlerin yerine geçer.

Kemik adları Sollumz'un kendi kemik kaydından gelir; doğrulamak için iskelet dosyası gerekmez.

## Sınırlar ve bilmen gerekenler

- Çıktı, Sollumz üzerinden dışa aktarılıp geri okunarak denetlendi; canlı bir FiveM sunucusunda ya da CodeWalker'da
  yüklenerek değil. Büyük bir paket yapmadan önce ilk varlığını oyunda dene.
- Dokular **`.ydr` içine gömülür**. Ayrı bir `.ytd` isteğe bağlıdır (**Also Write a YTD**, varsayılan kapalı, Sollumz
  2.8.3 ya da yenisi gerekir): testlerde Sollumz'un yazdığı `.ytd` dosyaları beklenenden çok küçük çıktı, bu yüzden
  varsayılan olarak kullanılmaz.
- MLO portal yönü Sollumz'u izler (portal adındaki ilk odadan bakınca saat yönünün tersi). CodeWalker'da bir portal ters
  görünürse iki oda adını yer değiştir.
- YMT dosyaları (ped metadata, örn. kıyafet `.ymt`) yazılmaz; Sollumz bunu desteklemez.
- Bu eklenti oyuna ya da bir sunucuya dokunmaz. Yalnızca varlık dosyaları yazar.
