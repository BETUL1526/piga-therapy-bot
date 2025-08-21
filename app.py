from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import time, random, os

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Seans değişkenleri
conversation_memory = []
session_start_time = None
SESSION_DURATION = 300  # 5 dakika
prep_shown = False  # hazırlık mesajı gösterildi mi?

# Ödev listesi
homeworks = [
    "Gün içinde seni zorlayan bir olayı seç ve bu sırada aklına gelen ilk otomatik düşünceyi not et. Sonra bunun yerine daha dengeli bir alternatif düşünce yaz.",
    "Bir hafta boyunca her gün, seni mutlu eden küçük bir olayı yazmayı dene.",
    "Zorlayıcı bir duygu hissettiğinde 5 dakika nefes egzersizi yapmayı dene. Sonra kendini nasıl hissettiğini yaz.",
    "Bu hafta en az bir kişiye duygu ve düşüncelerini açıkça ifade etmeyi dene, sonra süreci değerlendir.",
    "Her akşam günün en güzel 3 anını yaz, küçük şeyler bile olabilir."
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    global conversation_memory, session_start_time, prep_shown

    user_message = request.json.get("message")

    # Seans yeni başlıyorsa
    if session_start_time is None:
        session_start_time = time.time()
        prep_shown = False

    conversation_memory.append({"role": "user", "content": user_message})
    elapsed = time.time() - session_start_time

    # Bitime yakın hazırlık mesajı → sadece bir kere
    if 240 < elapsed < SESSION_DURATION and not prep_shown:
        prep_shown = True
        prep_message = (
            "Bugünkü sohbetimizi yavaş yavaş toparlamaya başlayabiliriz. "
            "Birazdan sana küçük bir özet ve denemen için bir ödev önereceğim."
        )
        return jsonify({"reply": prep_message, "end": False})

    # Seans süresi doldu → kapanış
    if elapsed >= SESSION_DURATION:
        joined = " ".join([m["content"] for m in conversation_memory if m["role"] == "user"])
        summary_prompt = (
            "Bir terapist gibi konuşmayı empatik, akıcı ve doğal bir dille özetle. "
            "Asla 'Selam' ya da yeni bir konuşma başlatan ifadelerle başlama. "
            "Kesinlikle 'kullanıcı' ya da 'kişi' deme; doğrudan 'sen' dilini kullan. "
            "Seans boyunca konuşulanları toparla, hangi duygulardan bahsedildiğini özetle. "
            "Sonra 'Bu haftaki seansımızın sonuna geldik' diyerek nazik bir sonlandırma yap. "
            "Sonrasında küçük bir ödev öner ve sıcak, destekleyici bir kapanış mesajı ver.\n\n"
            f"Konuşma: {joined}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": summary_prompt}],
            max_tokens=400
        )
        summary = response.choices[0].message.content.strip()

        homework = random.choice(homeworks)

        end_message = (
            f"{summary}\n\n"
            f"📌 Küçük bir ödev: {homework}\n\n"
            "🔮 Bir hafta sonra tekrar görüşmek istersen yeni bir seans başlatabilirsin. Buradayım. 💜"
        )

        # Reset session
        conversation_memory = []
        session_start_time = None
        prep_shown = False

        return jsonify({"reply": end_message, "end": True})

    # Normal cevap (Rogerian → Şema → BDT karışımı)
    prompt = (
        "Sen terapötik bir yapay zekâsın. Rogerian yaklaşımla başlayarak şema terapi "
        "ve BDT öğelerini harmanla. Tek cevapta yalnızca 1 soru sor. Empatik, doğal, "
        "insani ve destekleyici bir ton kullan. Gerektiğinde somutlaştırma, metafor ve "
        "yüzleştirme teknikleri kullan. Konuşma boyunca terapötik bağ kurmaya özen göster. "
        "Kısa ama içten cevaplar ver."
    )

    messages = [{"role": "system", "content": prompt}] + conversation_memory

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=180
    )

    reply = response.choices[0].message.content.strip()
    conversation_memory.append({"role": "assistant", "content": reply})

    return jsonify({"reply": reply, "end": False})


if __name__ == "__main__":
    app.run(debug=True)
