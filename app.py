<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kalkulator Pizza - System</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #e67e22;
            --sidebar-width: 250px;
            --bg-color: #f4f4f9;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            display: flex;
            background-color: var(--bg-color);
        }

        /* Sidebar / Menu */
        #sidebar {
            width: var(--sidebar-width);
            height: 100vh;
            background: #2c3e50;
            color: white;
            position: fixed;
            padding-top: 20px;
        }

        .menu-item {
            padding: 15px 25px;
            display: flex;
            align-items: center;
            cursor: pointer;
            transition: 0.3s;
            border-bottom: 1px solid #34495e;
        }

        .menu-item:hover {
            background: #34495e;
            color: var(--primary-color);
        }

        .menu-item i {
            margin-right: 15px;
            width: 20px;
            text-align: center;
        }

        /* Content Area */
        #main-content {
            margin-left: var(--sidebar-width);
            padding: 40px;
            width: 100%;
        }

        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 500px;
        }

        input[type="number"] {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }

        .btn-action {
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
    </style>
</head>
<body>

    <div id="sidebar">
        <div class="menu-item" onclick="location.reload()">
            <i class="fas fa-home"></i>
            <span>Główna</span>
        </div>
        
        <div class="menu-item" onclick="pobierzIZapisz()">
            <i class="fas fa-cloud-download-alt"></i>
            <span>Pobierz i Zapisz</span>
        </div>

        <div class="menu-item" onclick="pobierzDane()">
            <i class="fas fa-download"></i>
        </div>
        <div class="menu-item" onclick="ustawienia()">
            <i class="fas fa-cog"></i>
            <span>Ustawienia</span>
        </div>
    </div>

    <div id="main-content">
        <div class="card">
            <h2>Wprowadź kwotę</h2>
            <label>Kwota zamówienia (zł):</label>
            <input type="number" id="kwotaInput" step="0.01" placeholder="0.00" oninput="formatujKwote(this)">
            
            <button class="btn-action" onclick="oblicz()">Oblicz</button>
            <div id="wynik" style="margin-top:20px; font-weight:bold;"></div>
        </div>
    </div>

    <script>
        // Funkcja naprawiająca błąd z zerami
        function formatujKwote(input) {
            let value = input.value;
            
            // Jeśli użytkownik wpisze coś, co zaczyna się od 0, a nie jest ułamkiem (np. 05 -> 5)
            if (value.length > 1 && value.startsWith('0') && value[1] !== '.') {
                input.value = value.replace(/^0+/, '');
            }

            // Zapobiega wymuszaniu zera, gdy pole jest czyszczone
            if (value === "") {
                input.value = "";
            }
        }

        function pobierzIZapisz() {
            alert("Dane zostały pobrane i zapisane w bazie.");
            console.log("Akcja: Pobierz i Zapisz");
        }

        function pobierzDane() {
            alert("Pobieranie danych...");
            console.log("Akcja: Pobierz");
        }

        function oblicz() {
            const kwota = document.getElementById('kwotaInput').value;
            if(kwota) {
                document.getElementById('wynik').innerText = `Wprowadzona kwota: ${kwota} zł`;
            } else {
                document.getElementById('wynik').innerText = "Proszę wpisać kwotę.";
            }
        }

        function ustawienia() {
            alert("Otwieranie ustawień...");
        }
    </script>
</body>
</html>
