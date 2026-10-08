# UE5 varlık hattı: oyuna hazır varlıklar için beş eklenti

[English](ue5-pipeline.md) · [Genel bakışa dön](../README.tr.md)

Bu eklentiler "bitmiş model" ile "Unreal Engine 5'e aktarıldı" arasındaki adımları kapsar. Her biri bağımsızdır ve kendi yan
çubuk sekmesi vardır; birlikte en iyi çalışırlar, sonucu **UE5 Bridge** (kendi kılavuzuna bak) dışa aktarır.

| Eklenti | Yan çubuk sekmesi | Ne işe yarar |
|---|---|---|
| [Texture Kit](#texture-kit) | Texture Kit | Doku kontrolü, normal map çevirme, ORM paketleme, Unreal adlı dışa aktarma |
| [Texel Density](#texel-density) | Texel Density | Her varlığın doku yoğunluğunu ölç, renklendir ve ayarla |
| [Collision Maker](#collision-maker) | Collision | UBX / USP / UCP / UCX çarpışma şekilleri, denetleyici, mesh ile birlikte dışa aktarma |
| [Hard Surface Kit](#hard-surface-kit) | Hard Surface | Bevel, kesici, dizi, olak, temizlik, Stack'i Uygula |
| [Game Rig Kit](#game-rig-kit) | Game Rig | UE5 mannequin iskeleti, ağırlıklandırma, IK, yeniden adlandırma, animasyon retarget |

> **Bir varlık için önerilen sıra:** **Hard Surface Kit** ile modelle, **Texel Density**'yi ayarla, dokuları bake et ve
> **Texture Kit** ile kontrol et, **Collision Maker** şekillerini ekle, sonra **UE5 Bridge** ile dışa aktar. Karakterde önce
> **Game Rig Kit**, sonra aynı adımlar.

Beşi de Blender 5.0.1 ve 5.2.0'da test edildi. Hiçbiri Unreal Engine'in içinde denenmedi (burada kurulu değil); kurallar
Epic'in belgelerinden gelir.

## Texture Kit

Önlediği sorunlar: yeşil kanalı yanlış normal map'ler, veri olarak saklanan renk dokuları (ya da tersi), 2'nin kuvveti
olmayan boyutlar ve Unreal'a giden dağınık dosya yığını.

1. Objeyi seç. **Doctor** altında **Check Textures**'a bas. Kullanımına göre renk uzayı yanlış görüntüleri (normal, roughness
   ve metallic **Non-Color**, renk haritaları **sRGB** olmalı), eksik görüntüleri, 2'nin kuvveti olmayanları ve belirlediğin
   boyutu aşanları listeler. **Fix** ya da **Fix All** renk uzaylarını düzeltir; boyutları dışa aktarma düzeltir.
2. **Export Texture Set** altında klasörü, varlık adını, en büyük boyutu ve dosya biçimini seç.
   **Normal Map: Blender to Unreal** yeşil kanalı senin yerine çevirir (Blender OpenGL, Unreal DirectX ister).
   **Pack ORM** occlusion, roughness ve metallic'i tek dokunun kırmızı, yeşil ve mavi kanallarına koyar; occlusion haritasını
   **AO Image** alanından seç (materyalde bunun için giriş yoktur).
3. **Export for Unreal** `T_<ad>_BC` (base color), `T_<ad>_N`, `T_<ad>_ORM` ve `T_<ad>_E` (emission) dosyalarını sınırın
   içinde 2'nin kuvveti boyutlarda yazar; ayrıca her dosya için Unreal'da neyin ayarlanacağını (N için Normalmap sıkıştırma,
   N ve ORM için sRGB kapalı) söyleyen `T_<ad>_import_notes.txt` yazar.
4. **Channel Packer** başka görüntülerin dört kanalını tek yeni görüntüde birleştirir (örneğin glossiness haritasını ters
   çevirip roughness yapmak). **Normal Map** herhangi bir görüntünün yeşil kanalını çevirir.

Orijinal görüntülerin ve materyallerin hiçbir zaman değiştirilmez. Bake sonucu, kaydedilmemiş görüntüler güvenle işlenir.

## Texel Density

Texel yoğunluğu, bir metre yüzeyi kaç doku pikselinin kapladığıdır. Bir dünya ancak her yerde aynı olduğunda keskin ve tutarlı
görünür. Proplar için yaygın hedef **512 px/m**'dir (yaklaşık 5 px/cm).

1. **Target**'ı seç (128'den 4096 px/m'ye hazır değerler ya da kendi değerin) ve aktif objede **Measure**'a bas. Panel
   ortalama, en düşük ve en yüksek yoğunluğu, yüzeyin ne kadarının hedef dışı olduğunu, UV karesinin ne kadarının kullanıldığını
   ve kaç yüzün dışarıda kaldığını gösterir. Doku boyutu materyalin base color görüntüsünden (ya da varsayılandan) gelir.
2. **Show Colors** her yüzü boyar: **mavi** çok düşük, **yeşil** hedefte, **kırmızı** çok yüksek. **Hide Colors** kaldırır.
3. **Set Density** UV adalarını ölçekler. **Each Island** her adaya tam hedefi verir. **Whole Object** her şeyi birlikte
   ölçekler ve göreli boyutları korur. Edit Mode'da yalnızca seçili yüzler değişir.
4. **Copy from Active** seçili diğer objelere aktif objenin yoğunluğunu verir. **Pack Islands (Keep Density)** adaları
   boyutlarını değiştirmeden yerleştirir.

Önce yoğunluğu ayarla, sonra paketle; böylece sonradan hiçbir şey yeniden ölçeklenmez. UDIM tile'ları desteklenmez.

## Collision Maker

Unreal çarpışma şekillerini `UBX_` (kutu), `USP_` (küre), `UCP_` (kapsül) ve `UCX_` (dışbükey) adlı objelerden okur; ardından
mesh adı ve bir sayı gelir: `UBX_Crate_00`.

1. Bir mesh seç, **Shape** seç ve **Create Collision**'a bas. **Auto** uyan en basit şekli seçer: kutu, küre, kapsül, tek
   dışbükey kabuk ya da içbükey meshler için (simit, L biçimli oda) **Convex Parts**.
2. Şekiller mesh'in çocuğudur, tel kafes görünür ve render'dan gizlidir. **Box Fit** döndürülmüş ya da eksene hizalı olabilir;
   **Max Vertices** bir kabuğu sınırlar (Unreal 255 kabul eder); **Parts** Convex Parts'ın kaç kabuk kullanacağını belirler.
3. **Check Collision** Unreal'ın yok sayacağı ya da bozacağı şekilleri bulur: sahipsizler, dışbükey olmayan kabuklar, çok
   fazla vertex, nokta ya da boşluk içeren mesh adları. **Fix** kötü kabuğu dışbükey kabuğuyla değiştirir.
4. **UE5 Bridge** şekilleri mesh ile aynı FBX'e, eşleşen adlarla aktarır ve mesh'e göre konumlarını korur. Şekiller hiçbir
   zaman kendi başına mesh olarak aktarılmaz.

Convex Parts basit bir bölme yöntemi kullanır, tam bir yaklaşık dışbükey ayrıştırma değildir; çok karmaşık şekillerde sonucu
Unreal'ın çarpışma görünümünde kontrol et.

## Hard Surface Kit

Sıradan modifier'lardan kurulu, yıkıcı olmayan bir iş akışı: uygulayana kadar her şeyi değiştirebilirsin.

1. **Smart Bevel**: mesh'i **Smooth Angle** üstündeki kenarlarda sert olacak şekilde pürüzsüz gölgeler, bir Bevel modifier'ı
   (açıya ya da ağırlığa göre) ve bir Weighted Normal modifier'ı ekler, doğru sırada tutar. **Mark Sharp Edges** kenarları
   işaretler ve bevel ağırlığı verir.
2. **Cutters**: kesici objeleri seç, hedefi en son seç, **Use Selected as Cutters**'a bas (kes, ekle ya da kesişim).
   Kesiciler düzenlenebilir kalır, tel kafes görünür ve hedefi izler. **New Cutter** 3B imleçte kutu ya da silindir ekler.
   **Apply Cutters** kesimleri kalıcı yapar; **Remove Cutters** geri alır.
3. **Mirror and Arrays**: isteğe bağlı merkezden kesmeli ayna, doğrusal dizi ve objenin orijini çevresinde **dairesel dizi**
   (cıvata, havalandırma, tekerlek); çocuk bir empty tarafından yönlendirilir.
4. **Grooves and Cleanup** (Edit Mode): **Groove** ve **Panel** seçili yüzleri inset edip dik duvarlarla içeri ya da dışarı iter,
   bevel için kenarları sert işaretler. **Clean Mesh** çift vertex'leri birleştirir, serbest vertex'leri siler ve düz
   kenarları eritir.
5. **Apply Stack** özel normaller dahil her modifier'ı temiz bir mesh'e pişirir ve yardımcı objeleri siler. Shape key'li
   mesh'ler atlanır.

Kesiciler için etkileşimli çizim aracı yoktur; yukarıdaki araçlarla yerleştirir ve boyutlandırırsın.

## Game Rig Kit

Unreal Engine 5 mannequin iskeletini (standart Manny ve Quinn'in kemik adları ve hiyerarşisi) karakterinin üzerine kurar,
mesh'i ağırlıklandırır, IK ekler ve animasyonları retarget eder.

1. Karakter mesh'ini seç ve **Create Markers**'a bas. Standart insan oranlarında (-Y'ye bakan T-pozu) on iki empty belirir. Sol
   taraf işaretlerini modelinin eklemlerine taşı; sağ taraf yansıtılır.
2. **Build Rig** iskeleti kurar: root, pelvis, beş omurga kemiği, boyun, kafa, parmaklı kollar, ayak ve ball'lu bacaklar ve
   **IK Helper Bones** açıksa ik_foot ve ik_hand kemikleri. İşaretleri taşıdıktan sonra yeniden bas.
3. **Bind Meshes**: mesh'leri seç, rig'i en son seç. Otomatik ısı ağırlığı oluşturulur, sonra vertex başına **Max Influences**
   kemiğe (4 mobil sınırdır) indirilir, çok küçük ağırlıklar silinir, kalanlar normalize edilir. Mesh kapalı ve temiz
   olmalıdır; ısı ağırlığı başarısız olursa zarf ağırlığı kullanılır ve sana söylenir.
4. **Set Up IK** bacaklara ve kollara IK ekler: hedef kemikler, diz ve dirsek pole'ları ve dinlenme pozunu kıpırdatmayacak
   şekilde seçilen pole açısı. Ayak ve el hedeflerinin dönüşünü izler.
5. **Rename to UE5** Mixamo, Rigify ya da genel bir rig'i mannequin adlarına çevirir (vertex group'lar izler). **Create Mapping
   Sheet** eşleşmeyen kemikleri listeler; `kaynak kemik = ue kemiği` satırlarını yaz ve tekrar çalıştır.
6. **Retarget Animation**: **Source Rig**'i seç (action'lı), hedef rig'i seç ve düğmeye bas. Hareket, her kemiğin dinlenme
   pozundan ne kadar döndüğü olarak aktarılır; böylece farklı dinlenme pozlu rig'ler çalışır; pelvis hareketi boy oranıyla
   ölçeklenir.
7. **Check Skeleton** rig'i mannequin ile karşılaştırır: tek root, eksik kemikler, fazla kemikler, obje dönüşümü, adlar.

Sınırlar: twist kemiği, yüz rig'i ve ayak kilidi yok; parmaklar oranla yerleşir, kontrol et; retarget yalnızca dönüşleri (ve
pelvis konumunu) kopyalar.
