# Hard Surface Kit

Yıkıcı olmayan bir sert yüzey modelleme araç kutusu: bevel, kesici, dizi, olak, temizlik ve temiz bir Stack'i Uygula. Her 3B
projede kullanılabilen genel amaçlı bir eklentidir; Unreal Engine eklentilerinden hiçbirine ihtiyaç duymaz (Stack'i Uygula
sonucu yine de bir oyun motorunun istediği şeydir).

[English](hardsurface_kit.md) · [Genel bakışa dön](../README.tr.md)

Yan çubuk sekmesi: **Hard Surface**. Blender 5.0.1 ve 5.2.0'da test edildi.

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
