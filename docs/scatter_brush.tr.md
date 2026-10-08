# Scatter Brush (Serpiştirme Fırçası)

Çimen, taş, ağaç ya da istediğin herhangi bir modeli seviyeye iki yolla yay: zemine **vertex group boyayıp** modellerin
orada yumuşak bir yoğunluk geçişiyle çıkmasını sağla ya da viewport'ta **fırçayla tıklayıp sürükleyerek** elle yerleştir.
İkisi de aynı **kategorileri** kullanır: kategori, bir model takımıdır (örneğin 15 taş ya da 5 çimen modeli) ve onun için
kaydettiğin tüm rastgelelik ayarlarıdır.

[English](scatter_brush.md) · [Genel bakışa dön](../README.tr.md)

Panel, kenar çubuğunun **Scatter** sekmesindedir (3D görünümde `N`; ekran görüntülerinde resimler öyle çekildiği için
*Item* sekmesinin altında görünür). Blender 5.0.1 ve 5.2.0'da test edildi. Resimlerdeki sarı numaralar metindeki
numaralarla eşleşir.

## 1. Kategori oluştur

![Kategoriler](images/steps/scatter-1-category.png)

1. Modellerini seç (örneğin 5 çimen modeli) ve listedeki **+** düğmesine bas. Scatter Brush ilk modelin adıyla bir kategori
   açar ve modelleri **kendi collection'larına taşır** (`<ad> Assets`). Bu collection view layer'dan çıkarılır; böylece
   orijinaller seviyende durmaz ama kaynak olarak çalışmaya devam eder. Görünür kalmalarını istersen redo panelinde
   *Modelleri Gizle*'yi kapat. Her tür için bir kategori yap: Çimen, Taş, Ağaç.
2. **Modeller** aktif kategorinin collection'ını gösterir. Başka bir collection'a sürükleyebilir ya da daha fazla model
   ekleyebilirsin: objeleri seç ve **Seçileni Ekle**'ye bas (3, sol).
3. **Modelleri Hazırla** (3, sağ) her modelin ölçek ve döndürmesini uygular, origin'i **alt ortaya** koyar. Bir kez yap:
   origin, zemine değen noktadır ve rastgele ölçek objenin zaten sahip olduğu ölçekle çarpılır. Bir modelin buna ihtiyacı
   olunca kırmızı bir uyarı çıkar. Mesh'ini başka bir objeyle paylaşan, parent'ı olan ya da mesh olmayan modeller atlanır ve
   mesajda sayılır.

## 2. Rastgelelik (iki kipte de aynı)

![Çeşitlilik ve fırça ayarları](images/steps/scatter-2-brush.png)

Buradaki her şey aktif kategoriye aittir ve dosyayla birlikte kaydedilir. Her objenin modeli kategoriden rastgele seçilir.

| # | Ayar | Ne yapar |
|---|---|---|
| 1 | **En Küçük / En Büyük Boyut** | Her obje iki değer arasında rastgele bir boyut alır. **Boy Farkı** bunun üstüne sadece boyu uzatır; bitkiler genişlikten çok boyda farklılaşır. |
| 2 | **Rastgele Dönüş / Rastgele Eğilme** | Yukarı eksen etrafındaki en büyük rastgele dönüş (360 serbest dönüştür) ve ekseninden en büyük rastgele eğilme. |
| 3 | **Yüzeye Hizala** | 0 her şeyi dik tutar, 1 zeminin eğimini izler. |
| 4 | **Gömme**, **Tohum** | Objeleri zemine gömer (yarı gömülü taş) ve rastgele desen. Ok düğmesi yeni tohum seçer. |
| 5 | **Fırçayı Başlat** | Tıklama fırçası, 4. bölüme bak. |
| 6 | **Yarıçap, Tıklama Başına Obje, Sürükleme Aralığı, En Az Mesafe, En Çok Eğim** | Tıklama fırçası ayarları, 4. bölüme bak. |
| 7 | **Sil** | Fırçayı silme kipine alır (ayrıca: `Shift` basılı tut ya da `E`). |
| 8 | **Yerleştirilenleri Sil** | Fırçanın ya da bake'in bu kategori için yerleştirdiği her objeyi siler. |

## 3. Ağırlık boyadığın yere serpiştir

![Weight paint katmanları](images/steps/scatter-3-weights.png)

1. **Zemin mesh'ini** seç ve kategoriyi seç (örneğin *Grass*). Grup listesindeki **+** (4) ile zeminde bir vertex group aç,
   adını ver (`grass`) ve seçili bırak. **Önce zeminin ölçek ve döndürmesini uygula** (`Ctrl+A`): objeler zeminin
   uzayında yaşar ve ikisini de miras alır. Gerekince kırmızı bir uyarı çıkar.
2. **Yüzey Katmanı Ekle**'ye bas (5). Katman aşağıda belirir (6), kullandığı grupla birlikte (7). Grup boş olduğu için
   henüz bir şey çıkmaz: ağırlığı her yerde 0'dır.
3. Katmanın **weight paint** simgesine bas (6, görünürlük simgesinden sonraki ilk simge). Blender o grupla Weight Paint'e
   geçer; çimenin tam olmasını istediğin yeri ağırlık 1 ile, sönmesini istediğin yeri daha azıyla boya. Boyarken modeller
   canlı olarak belirir (1). İşin bitince Object Mode'a dön.
4. Alan **yumuşakça söner**: yoğunluk, yüz yüz değil, her yüzün her noktasındaki ağırlığı izler (2). Panelden ayarla (3):

   | Ayar | Ne yapar |
   |---|---|
   | **Yoğunluk** | Ağırlığın 1 olduğu yerde metrekare başına obje. Katmandaki **Yoğunluk ×** (8) bunu sadece o zemin için çarpar. |
   | **Kenar Sönümü** | 1 ağırlığı doğrusal izler, 2 ve üstü zayıf ağırlıklara doğru objeleri daha hızlı seyreltir; yamanın kenarı sıkılaşır. |
   | **Ağırlık Eşiği** | Bu değer ve altındaki ağırlıklara hiç obje konmaz. |
   | **Kenarda Küçült** | Ağırlığın zayıf olduğu yerde objeler küçülür; çimenliğin kenarı kısa çimenden oluşur. |
   | **Eşit Aralık / En Az Mesafe** | İki obje arasında en az bu mesafeyi korur (ağaç ve taş için iyi; biraz daha yavaş). |

5. Başka kategoriler için daha fazla katman ekle (`rocks` grubunda Taş, `trees` grubunda Ağaç). Katman bir Geometry Nodes
   modifier'ıdır; ekran simgesi kapatır, çarpı kaldırır. Ağırlık alanını boş bırakırsan tüm yüzeye serpiştirir.
6. **Objelere Dönüştür** (6, ortadaki simge) katmanı taşıyabileceğin, silebileceğin ya da tek tek dışa aktarabileceğin
   gerçek objelere çevirir. Bunlar bağlı kopyalardır (modelin mesh'ini paylaşır), `<kategori> Placed` collection'ına konur
   ve katman kaldırılır (redo paneli katmanı tutabilir). 20 000'den fazla obje reddedilir: önce yoğunluğu düşür.

## 4. Tıklama fırçası

![Tıklama fırçası](images/steps/scatter-4-brush.png)

Bir kategori seç ve **Fırçayı Başlat**'a bas (3). Yeşil daire farenin altındaki yüzeyi izler ve tümseklerin üstüne oturur (2).

| Eylem | Sonuç |
|---|---|
| Sol tık | Dairenin içine **Tıklama Başına Obje** kadar obje koyar (1); her biri kategorideki rastgele bir model, boyut, dönüş ve eğilmeyle gelir. |
| Sol tık + sürükle | Fare **Sürükleme Aralığı** × yarıçap kadar gittikçe yeniden yerleştirir. |
| `Shift` + sol tık ya da `E` | Silme kipi: dairenin içindeki, kategorinin fırça objelerini kaldırır (daire kırmızı olur). |
| `Ctrl` + tekerlek ya da `[` ve `]` | **Yarıçapı** değiştirir. Tek başına tekerlek ve orta tuş görünümü hareket ettirmeye devam eder. |
| `Esc`, `Enter` ya da sağ tık | Aracı bitirir. |

Ayarlar (4): **Yarıçap** (0 tam imlecin olduğu yere koyar), **Tıklama Başına Obje**, **Sürükleme Aralığı**, **En Az Mesafe**
(hiçbir iki obje bundan yakın olmaz; önceki fırça darbelerindeki objeler dahil) ve **En Çok Eğim** (daha dik zemini atlar,
uçurumda çimen olmaz). Her fırça darbesi tek bir geri alma adımıdır. Fırça zemini ararken kendi objelerini yok sayar; bu
yüzden daha önce doldurduğun alanın üstünden de boyayabilirsin.

Yerleştirilen objeler `<kategori> Placed` içindeki sıradan bağlı kopyalardır; Blender'ın geri kalanı (taşı, sil, dışa
aktar) onlarla her obje gibi çalışır.

## Sınırlar, dürüstçe

- **Modellerin hazırlanması gerekir.** Kaynak objenin ölçek ve döndürmesi katmanlarda ve fırçada yok sayılır; origin zemine
  değen noktadır. **Modelleri Hazırla**'yı kullan.
- **Yüzey katmanlarında zeminin ölçeği 1, döndürmesi 0 olmalı.** Tıklama fırçası bunu umursamaz.
- Yoğunluk, zemin yüzeyinin metrekaresi başınadır. Çok seyrek bir zemin mesh'i (birkaç büyük yüz) sönümün boyamanı ne kadar
  iyi izlediğini sınırlar; ağırlıklar her yüzün içinde ara değerlenir.
- Her objenin modeli eşit olasılıkla rastgele seçilir. Model başına ağırlık yoktur.
- **En Az Mesafe** (fırça) ya da **Eşit Aralık** (katman) ayarlamazsan objeler birbirinden ve başka katmanlardan kaçınmaz.
- Canlı katmanlar sadece Blender'da vardır. Unreal Engine için önce **Objelere Dönüştür**. Binlerce tek obje ağır bir FBX
  demektir; yaprak/çimen için modelleri bir kez dışa aktarıp Unreal içinde yeniden serpiştirmeyi tercih edebilirsin. Burada
  Unreal'da denenmedi.
- Tıklama fırçası Object Mode ve bir 3D viewport ister; kalem basıncı desteği yoktur.
- Blender 5.0.1 ve 5.2.0'da betikli kontrollerle doğrulandı (bağımsız bir hesapla obje sayıları, ölçek ve dönüş aralıkları,
  eğimler, aralık, bake) ve tıklama fırçası gerçek bir pencerede simüle edilmiş fare olaylarıyla denendi.
