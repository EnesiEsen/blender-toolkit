# Terrain Blend

Tek mesh üzerinde istediğin sayıda PBR doku setini karıştırır. Her set (çim, patika, kaya, çamur ...) bir **katmandır**;
bir **vertex group** katmanın nerede görüneceğini söyler. Eklenti materyali ve küçük bir Geometry Nodes modifier'ı senin
yerine kurar, her şeyi canlı sürgülerle ayarlanabilir bırakır.

[English](terrain_blend.md) · [Genel bakışa dön](../README.tr.md)

![Terrain Blend paneli](images/terrain_blend.png)

## Hızlı başlangıç

1. Arazi mesh'ini seç. **Her yüzey için bir vertex group** aç (`path`, `rock`, `mud` ...) ve ağırlık boya; ya da
   eklentiye ürettir (4. adım).
2. Her doku setini kendi klasöründe tut. Eklenti haritaları dosya adından bulur; ambientCG, Poly Haven, Poliigon, Quixel
   veya Substance'tan indirdiklerin olduğu gibi çalışır:

   | Harita | Dosya adında tanınan sözcükler |
   |---|---|
   | Color | `color`, `col`, `basecolor`, `albedo`, `diffuse`, `diff` |
   | Normal | `normal`, `normalgl`, `normaldx`, `nor`, `nrm`, `norm` (OpenGL, DirectX'e tercih edilir) |
   | Roughness | `roughness`, `rough` |
   | Height | `height`, `displacement`, `disp`, `bump` |

   Bir set için en az color haritası gerekir. Olmayan haritalar atlanır.
3. **Terrain Blend** panelini aç, **Add From Texture Library**'ye bas ve set klasörlerini içeren klasörü seç. Color
   haritası olan her alt klasör bir katman olur; aynı adlı vertex group o katmanın maskesi olur. İlk katman **tabandır**,
   maske istemez. (**Add From Vertex Groups** tersini yapar: her vertex group için bir katman açar, doku klasörlerini
   sen seçersin.)
4. Bir katman seç ve **Generate Mask**'e bas: vertex group'u elle boyamak yerine **eğim**, **yükseklik** veya **gürültü**
   ile doldurur. Aralığı (From / To) seç, ters çevir ya da mevcut ağırlıkla birleştir (değiştir, kesişim, birleşim).
5. **Build / Update Material**'e bas. Materyal ve **TB Masks** modifier'ı oluşur.
6. Sonucu **Live Settings** sürgüleriyle ayarla. Yeniden kurmak gerekmez.

## Adım adım rehber: sıfırdan bir arazi

Bu rehber tek bir örnekle ilerler: çimen bir zemin, içinden geçen bir patika, bir çamur lekesi ve dik yamaçta kaya.
Görsellerdeki sarı numaralar metindeki numaralarla aynıdır. Aynı adımları kendi araziniz için uygulayın.

> **Panel nerede?** 3B görünümde `N` tuşuyla yan çubuğu açın ve **Terrain Blend** sekmesine tıklayın. Ekran görüntülerinde panel,
> görüntüleri alma yöntemi yüzünden **Item** sekmesinin altında görünür; sizin Blender'ınızda kendi sekmesindedir.

### 1. Hazırlık: mesh, UV ve doku klasörleri

- **Mesh sık olmalı.** Maske vertex başınadır; geçiş bölgesinde mesh ne kadar sıksa geçiş o kadar yumuşak olur. Deneme için
  *Add > Mesh > Grid* ekleyip X ve Y Subdivisions değerini 100 – 200 yapın.
- **UV:** Mesh'te UV haritası varsa dokular onunla kaplanır. Yoksa nesne koordinatları (Generated) kullanılır.
- **Doku klasörleri:** Her doku setini kendi klasörüne koyun ve klasörlere vertex group adlarıyla aynı adı verin:

```
Dokular/
  grass/  grass_Color.jpg  grass_NormalGL.jpg  grass_Roughness.jpg  grass_Displacement.jpg
  mud/    mud_Color.jpg    ...
  path/   path_Color.jpg   ...
  rock/   rock_Color.jpg   ...
```

- **Taban katman:** Katmanlar klasör adına göre alfabetik eklenir ve ilk katman taban olur. Burada `grass` ilk olduğu için
  otomatik taban olur. Taban başka bir set olacaksa katmanı sonradan okla yukarı taşıyın.

### 2. Vertex group'ları oluşturun ve boyayın

![Weight Paint ile patika boyama](images/steps/terrain-1-paint.png)

1. Mesh'i seçin. Sağ alttaki Properties editöründe **Object Data** sekmesine (yeşil üçgen) girin, **Vertex Groups**
   bölümünde `+` ile her yüzey için bir grup açın: `path`, `mud`, `rock`. Taban (`grass`) için grup gerekmez.

   ![Vertex Groups listesi](images/steps/terrain-1-groups.png)

2. Üstteki mod menüsünden **Weight Paint**'e geçin, listeden grubu seçin ve fırçayla boyayın. **Kırmızı = katman tam
   görünür**, **mavi = görünmez** (yukarıdaki görselde 1). Patika gibi ince şeritleri elle boyamak en iyi sonucu verir.
3. İşiniz bitince **Object Mode**'a dönün. Terrain Blend paneli (görselde 2 ile işaretli düğmelerin olduğu yer) N
   panelinde, **Terrain Blend** sekmesindedir.

> Boyamak istemediğiniz gruplar için 4. adımdaki **Generate Mask** kullanılabilir.

### 3. Katmanları ekleyin

1. **Add From Texture Library**'ye basın (görselde 2) ve `Dokular` klasörünü seçin.
2. `grass`, `mud`, `path`, `rock` katmanları oluşur. Aynı adlı vertex group her katmanın maskesi olur (aşağıdaki görselde 5).
3. Satırlara bakın: soldaki **kırmızı uyarı simgesi** katmanın doku klasörünün eksik olduğunu, sağdaki *no mask* yazısı maskenin
   seçilmediğini gösterir. Katmanı seçip alttaki **Name / Texture / Mask** alanlarından tamamlayın.

*Alternatif:* Önce vertex group'ları açtıysanız **Add From Vertex Groups** her grup için bir katman açar; doku
klasörlerini kendiniz seçersiniz.

### 4. Maskeleri otomatik üretin

![Eğimden kaya maskesi](images/steps/terrain-3-slope.png)

Kaya yalnızca dik yamaçlarda görünsün:

1. `rock` katmanını seçin ve **Generate Mask**'e basın.
2. Pencerede *Vertex Group* `rock`, *Source* **Slope**, *From* **25**, *To* **45** yazın ve onaylayın.
3. Sonuç yukarıdaki görseldeki gibidir: **1** dik yer (kırmızı, kaya görünür), **2** düz yer (ağırlık 0).

Başka reçeteler:

| İstediğiniz | Source | From – To | Not |
|---|---|---|---|
| Dik yamaçta kaya | Slope | 25 – 45 (derece) | 0 = düz, 90 = dik duvar |
| Yüksek yerde kaya ya da kar | Height | 8 – 14 (metre) | Dünya yüksekliği; nesneyi taşırsanız değişir |
| Düz ovada çimen | Slope + **Invert** | 20 – 40 | Dik olmayan yerler |
| Dağınık çamur lekeleri | Noise | 0.4 – 0.6 | *Noise Scale* leke boyunu, *Seed* deseni değiştirir |
| Dik **ve** yüksek | Slope sonra Height | *Combine*: **Intersect** | İki koşulun kesişimi |
| Dik **ya da** yüksek | Slope sonra Height | *Combine*: **Union** | İki koşulun birleşimi |

Boyadığınız maske ile otomatik maskeyi birleştirmek için *Combine* seçeneğini kullanın; *Replace* eskiyi siler.

### 5. Materyali kurun ve sonucu görün

![Terrain Blend sonucu](images/steps/terrain-2-result.png)

1. **Build / Update Material**'e basın (görselde 9). `<nesne adı> Terrain` adlı bir materyal ve **TB Masks** modifier'ı oluşur.
2. 3B görünümü **Material Preview**'e alın (başlıktaki küre simgeleri). Sonuç yukarıdaki gibi olmalı: **1** çimen (taban),
   **2** çamur, **3** patika, **4** kaya.
3. Listede bir katman seçince **Live Settings** (görselde 10) o katmanın ayarlarını gösterir. Bunları değiştirmek için
   yeniden kurmak gerekmez.

### 6. Görünümü ayarlayın

| Sorun | Ne yapmalı |
|---|---|
| Doku çok büyük ya da çok küçük | Katmanın **Scale** değeri: büyütünce doku sıklaşır (küçülür). Çimen için 40 – 80, kaya için 15 – 25 deneyin |
| Geçişler fırça izi gibi düz | **Noise** ve **Height Influence** değerlerini artırın; kenar doku yüksekliğine göre dağılır |
| Geçiş kenarı çok keskin | **Softness** değerini artırın |
| Yüzey fazla düz | **Relief (m)** ve **Normal Strength** değerlerini artırın |
| Her yerde aynı desen görünüyor | **Blend Noise Scale** değerini değiştirin, **Texture Enhancer**'ı açın |

**Texture Enhancer** (görselde 8'in altındaki kutu) ek dosya gerektirmeden ince detay, çatlaklarda kir ve mikro kabartma
ekler; sürgüleri Live Settings'in en altında *Enhancer* adıyla durur. **Lite Preview** ise yalnızca renk ve yükseklik
haritalarını kullanır: OpenGL arka uçlu EEVEE'de (Blender 5.0) çok katmanda yüzeyin pembe görünmesini önler. Son görünüm
için kapatın.

### 7. Render alın

- **EEVEE:** 49 katmana kadar çalışır. Blender 5.2'de **Preferences > System > GPU Backend: Vulkan** seçin.
- **Cycles:** Gerçek kabartma için *Material Properties > Settings > Surface > Displacement* alanını
  **Displacement and Bump** yapın ve mesh'in sık olduğundan emin olun.

### 8. Sonradan değişiklik

- **Yeni yüzey:** Yeni vertex group açın, `+` ile katman ekleyin, klasör ve maske seçin, **Build / Update Material**'e
  basın. Sürgü değerleriniz korunur.
- **Katman silmek veya sıra değiştirmek:** `-` ve oklar. Listede aşağıdaki katman üsttekinin üstüne boyanır.
- **Modifier silindiyse:** **Build / Update Material** onu geri getirir.

### Sık karşılaşılan sorunlar

| Belirti | Sebep ve çözüm |
|---|---|
| Yüzey pembe | EEVEE doku sınırı aşıldı. **Lite Preview**'i açın, Vulkan'a (5.2) geçin ya da Cycles kullanın |
| Bir katman hiç görünmüyor | Maske vertex group'u boş ya da adı yanlış. Weight Paint'te kontrol edin, katmanın **Mask** alanını doldurun |
| "Texture ... not found" | Klasörde dosya adında `Color`, `Albedo`, `Diffuse` gibi tanınan bir sözcük yok |
| Yüzey ters aydınlanıyor | DirectX normal haritası kullanılıyor. Klasöre OpenGL (`NormalGL`) sürümünü koyun |
| Geçişler kare kare görünüyor | Mesh çok seyrek. Subdivide edin ya da daha sık bir grid kullanın |
| .blend'i başkasına verince doku yok | Dokular klasörden okunur. **File > External Data > Pack Resources** kullanın |

## Panel başvurusu

| Kontrol | Ne yapar |
|---|---|
| Katman listesi (+ / - / oklar) | Katman ekle, sil, sırala. Sonraki katmanlar öncekilerin üstüne boyanır. |
| Name, Texture Folder, Mask | Katman adı, doku seti klasörü ve nerede görüneceğini belirleyen vertex group. |
| Generate Mask | Maskeyi eğimden (derece), yükseklikten (metre) veya gürültüden (0–1, ölçek ve seed ile) doldurur. |
| Lite Preview | Yalnızca color ve height haritalarını kullanır (katman başına 2 doku). OpenGL arka uçlu EEVEE'de çok katman için kullan. Son görünüm için kapat. |
| Texture Enhancer | Dokuların üstüne prosedürel ince detay normali, çatlak kiri ve mikro displacement ekler. Ek görsel dosya gerekmez. |
| Build / Update Material | Materyali ve modifier'ı yeniden kurar. Ayarladığın sürgü değerleri korunur. |

**Live Settings** (genel): Blend Noise Scale (katman kenarlarını dağıtır), Normal Strength, Relief (metre cinsinden
yükseklik). **Katman başına**: Scale (doku tekrarı), Softness, Height Influence (height haritasının geçişi itmesi),
Noise. **Enhancer**: Detail Strength ve Scale, Dirt Amount ve Scale, Dirt Color, Micro Displacement ve Scale.

## Kaç katman kullanabilirim?

Eklenti sınır koymaz. Sınırlar render motorundan gelir; panel o sınıra varmadan seni uyarır:

| Motor | Sınır | Ne yapmalı |
|---|---|---|
| Cycles | Önemli bir sınır yok | Son render için bunu kullan. |
| EEVEE, Vulkan arka uç (Blender 5.2) | 256 dokuya, 49 katmana kadar | Büyük setler için yeterli. |
| EEVEE, OpenGL arka uç (Blender 5.0 ya da OpenGL'deki 5.2) | Yaklaşık 30 doku. Katman başına 4 harita ile bu 7 katmandır; üstünde yüzeyler pembe olur | **Lite Preview**'i aç (katman başına 2 harita, 14 katman) ya da Cycles kullan. |
| EEVEE, her arka uç | 49 katman (GPU öznitelik sınırı: maskeler 4'erli paketlenir) | Daha fazlası için Cycles. |

Blender 5.0.1 ve 5.2.0'da 14 ve 49 katmanlı materyallerle test edildi.

## Bilmen gerekenler

- Maskeler shader'a **TB Masks** adlı bir Geometry Nodes modifier'ı ile ulaşır. Onu uygular ya da silersen
  **Build / Update Material**'e basarak geri getir.
- Blender 5.0 EEVEE, materyalde vertex group'u doğrudan okuyamaz. Bu yüzden eklenti onları renk özniteliklerine paketler.
  Yapacağın bir şey yok; 5.0 ve 5.2'de aynı çalışır.
- Her obje kendi katman listesini tutar; farklı araziler farklı set kullanabilir.
- Dokular kopyalanmaz, klasörlerinden okunur. Klasörleri yerinde bırak ya da .blend dosyasını paylaşmadan önce
  **File > External Data > Pack Resources** kullan.

## Sınırlar

- Taban katman her zaman tüm mesh'i kaplar.
- Otomatik maskeler vertex başına çalışır; düşük poligonlu mesh kaba maske verir. İnce kontrol için mesh'i böl ya da
  grubu elle boya.
- Testler yaklaşık on bin vertex'lik ızgaralar kullanır. Materyal vertex sayısına bağlı değildir, ama **Generate Mask**
  her vertex'i dolaşır; çok yoğun mesh'lerde daha uzun sürer.
