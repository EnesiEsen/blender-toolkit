# Retopo Kit

Her model için tek tıkla quad retopoloji: basit proplar, sert yüzey araçlar, karakterler. İsteğe bağlı rehber eğriler
sonucun kenar akışının nereden geçeceğini söyler (göz, ağız, parmak, panel aralıkları). Kalite raporu sonucun temiz olup
olmadığını gösterir.

[English](retopo_kit.md) · [Genel bakışa dön](../README.tr.md)

![Retopo Kit paneli](images/retopo_kit.png)

## Hızlı başlangıç

1. Yüksek poligonlu ya da dağınık mesh'i seç.
2. Bir **Preset** seç (ya da **Auto** bırak) ve **Target Faces** değerini ayarla.
3. **Retopologize**'a bas. `<ad>_retopo` adlı yeni bir obje oluşur ve seçilir; orijinalin korunur ve gizlenir (görünür
   kalsın istersen **Hide Source**'u kapat).
4. **Quality Report** bölümünü aç ve **Analyze Mesh**'e basarak sonucun ne kadar temiz olduğuna bak.

## Ön ayarlar

| Ön ayar | Ne için | Ne yapar |
|---|---|---|
| Auto | Her şey | Mesh'te kaç keskin kenar olduğuna bakar, Hard Surface ya da Organic seçer. |
| Simple Prop | Kutu, sandık, basit şekiller | Keskin kenarları (30 derece) ve sınırı korur, ek yumuşatma yok. |
| Hard Surface / Vehicle | Makine, araç, mimari | Keskin kenarları net tutar (30 derece), yumuşatma yok. |
| Organic / Character | Karakter, yaratık, sculpt | Yumuşak akış (80 derece), yumuşatma açık; yalnızca seam'ler sert çizgi olur. |

Ön ayar seçmek **Sharp Angle** ve **Smoothing** değerlerini ayarlar; sonra **Advanced** altında değiştirebilirsin.

## Motorlar

| Motor | Güçlü yanı | Not |
|---|---|---|
| QuadriFlow | Blender'a dahil, hızlı | Rehber eğrileri yok sayar. |
| QRemeshify | Daha iyi kalite, keskin kenarları **ve rehber eğrileri** izler | Ayrı, ücretsiz eklenti ([ksami/QRemeshify](https://github.com/ksami/QRemeshify)). |
| Auto (varsayılan) | Kuruluysa QRemeshify, değilse QuadriFlow kullanır | Panel hangisinin kullanıldığını söyler. |

## Rehber eğriler

Rehberler, yeni quad'ların izlemesi gereken çizgilerdir. QRemeshify ile çalışır.

1. **Guides** alt panelini aç.
2. **Draw Guide** bir eğri oluşturur ve Blender'ın Draw aracını yüzeye izdüşümle başlatır: modelin üstünde sürükleyerek
   çiz (gözün etrafı, ağız boyunca, panel aralığı boyunca). Her çizgi için tekrarla.
3. **Apply Guides** seçili eğrileri hedef mesh üzerinde rehber kenarlara çevirir (eğri noktaları arasında mesh
   kenarları boyunca en kısa yol). Ya da Edit Mode'da kenarları seçip **Mark Selected Edges**'e bas.
4. **Use Guides** açıkken **Retopologize**'a bas. İşaretlediğin kenarlar, yeni topolojinin izlediği sert çizgiler olur.
5. **Clear Guides** işaretleri kaldırır ve mesh'in önceki seam ve keskin kenarlarını geri yükler.

## Diğer kontroller

| Kontrol | Ne yapar |
|---|---|
| Symmetry X / Y / Z | Sonuca o eksende bir Mirror modifier ekler. |
| Snap to Source | Sonraki düzenlemeler kaynak yüzeyde kalsın diye Shrinkwrap modifier'ı (`RK Snap`) ekler. |
| Hide Source | Retopolojiden sonra orijinali gizler. |
| Match Target | İlk sonuç Target Faces'ten uzaksa ikinci geçiş yapar (QRemeshify). |
| Sharp Angle | Bundan keskin kenarlar sert çizgi olarak kalır. |
| Smoothing | Quad'a çevirmeden sonra sonucu yumuşatır. |
| Retopology overlay | Blender'ın retopoloji katmanını görünümde gösterir. |

## Kalite raporu

**Analyze Mesh** aktif mesh'i ölçer:

- yüz sayısı ile quad, üçgen ve n-gon oranı
- pole'lar (3, 5 veya 6+ kenarın birleştiği vertex'ler)
- kenar uzunluğu değişimi (düşük = daha düzgün quad'lar)
- kaynak yüzeye uzaklık, ortalama ve en büyük, model boyutunun yüzdesi olarak
- non-manifold kenarlar

Yüzlerin %90'ından azı quad ise uyarı çıkar: **Target Faces**'i artır ya da rehber ekle.

## İpuçları

- Retopolojiden önce serbest parçaları ve iç yüzleri temizle; motorlar temiz, kapalı yüzeyde en iyi çalışır.
- Çok yoğun mesh'ler (yaklaşık 90.000 üçgenin üstü) önce bir çalışma kopyasında otomatik seyreltilir, çok seyrekler
  (yaklaşık 2.500'ün altı) bölünür; böylece motorlara makul bir girdi gider. Orijinaline dokunulmaz.
- Karakterde gövdeyi ve kıyafeti ayrı objeler olarak retopolojiye sok.
- Retopoloji iyi bir temel verir, bitmiş animasyon mesh'i değil. Eklem çevresindeki kenar döngülerini kendin kontrol et.

## Sınırlar

- Rehber eğriler QRemeshify ister; QuadriFlow ile yok sayılır ve panel bunu söyler.
- Farklı motor ya da sürümler aynı sonucu vermez.
- Testlerde kullanılan QRemeshify yapısı Windows içindir. macOS ve Linux'ta uygun QRemeshify yapısını kur; Retopo Kit
  düz Python'dur ve QuadriFlow'a geri düşer.
