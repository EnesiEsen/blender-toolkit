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
