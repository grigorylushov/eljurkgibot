<?php
session_start();

$host = 's5ql5307.infi5nityfree.com';
$dbname = 'i5f0_39061654654882_elj5ur';
$username = 'if0_3905465465461882';
$password = 'jpX9rb5465464565466Og91WR9e9';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    die("Ошибка подключения к базе данных: " . $e->getMessage());
}

function isLoggedIn() {
    return isset($_SESSION['user_id']);
}

function isAdmin() {
    return isset($_SESSION['role']) && $_SESSION['role'] === 'admin';
}

function isTeacher() {
    return isset($_SESSION['role']) && $_SESSION['role'] === 'teacher';
}

function isStudent() {
    return isset($_SESSION['role']) && $_SESSION['role'] === 'student';
}

function isParent() {
    return isset($_SESSION['role']) && $_SESSION['role'] === 'parent';
}

function hasPermission($requiredRole) {
    if (!isLoggedIn()) return false;
    return $_SESSION['role'] === $requiredRole;
}

// Функция для генерации кода приглашения
function generateInviteCode($length = 8) {
    return strtoupper(substr(md5(uniqid(mt_rand(), true)), 0, $length));
}

// Функция для редиректа с сообщением
function redirectWithMessage($url, $type, $message) {
    $_SESSION[$type] = $message;
    header("Location: $url");
    exit();
}

// ... существующий код ...

// Функции для работы с уведомлениями
function setFlashMessage($type, $message) {
    $_SESSION[$type] = $message;
}

function getFlashMessage($type) {
    $message = $_SESSION[$type] ?? '';
    unset($_SESSION[$type]);
    return $message;
}

// Функция для проверки и показа уведомлений
function displayFlashMessages() {
    $types = ['success', 'error', 'warning', 'info'];
    $icons = [
        'success' => 'check-circle-fill',
        'error' => 'exclamation-circle-fill', 
        'warning' => 'exclamation-triangle-fill',
        'info' => 'info-circle-fill'
    ];
    
    $html = '';
    foreach ($types as $type) {
        if ($message = getFlashMessage($type)) {
            $html .= '
            <div class="alert alert-'.$type.' alert-dismissible fade show">
                <i class="bi bi-'.$icons[$type].'"></i>
                '.$message.'
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>';
        }
    }
    return $html;
}
// Функция перенаправления на страницу ошибки
function redirectToError($errorCode = 404, $message = '') {
    $errorPages = [
        403 => '403.php',
        404 => '404.php',
        500 => '502.php',
        502 => '502.php',
        503 => '502.php'
    ];
    
    $page = $errorPages[$errorCode] ?? '404.php';
    
    if (!empty($message)) {
        $_SESSION['error_message'] = $message;
    }
    
    header("Location: $page");
    exit();
}

// Пример использования в коде:
// if (!isAdmin()) {
//     redirectToError(403, 'Требуются права администратора');
// }


// Удаляем настройки Яндекс
// define('YANDEX_CLIENT_ID', 'ваш_client_id_здесь');
// define('YANDEX_CLIENT_SECRET', 'ваш_client_secret_здесь'); 
// define('YANDEX_REDIRECT_URI', 'http://ваш-домен/yandex_callback.php');

// Удаляем функции Яндекс
// function generateCsrfToken() {
//     if (empty($_SESSION['csrf_token'])) {
//         $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
//     }
//     return $_SESSION['csrf_token'];
// }

// function verifyCsrfToken($token) {
//     return isset($_SESSION['csrf_token']) && hash_equals($_SESSION['csrf_token'], $token);
// }

// function getYandexAuthUrl() {
//     $params = [
//         'response_type' => 'code',
//         'client_id' => YANDEX_CLIENT_ID,
//         'redirect_uri' => YANDEX_REDIRECT_URI,
//         'scope' => 'login:email login:info',
//         'state' => generateCsrfToken()
//     ];
//     return 'https://oauth.yandex.ru/authorize?' . http_build_query($params);
// }

// Добавляем настройки VK
define('VK_CLIENT_ID', 'ваш_client_id_vk');
define('VK_CLIENT_SECRET', 'ваш_client_secret_vk');
define('VK_REDIRECT_URI', 'http://ваш-домен/vk_callback.php');
define('VK_API_VERSION', '5.199');

// Функция для получения URL авторизации VK
function getVkAuthUrl() {
    $params = [
        'client_id' => VK_CLIENT_ID,
        'redirect_uri' => VK_REDIRECT_URI,
        'response_type' => 'code',
        'scope' => 'email', // запрашиваем email
        'v' => VK_API_VERSION,
        'state' => bin2hex(random_bytes(16)) // простая защита
    ];
    return 'https://oauth.vk.com/authorize?' . http_build_query($params);
}

// ... остальной код config.php без изменений ...
// Добавляем в config.php
define('TELEGRAM_BOT_API_KEY', '7994222730:AAG7PJ_qL6ST_iFeEh46546G19ZfVkgfkCMYmmc');
define('TELEGRAM_WEBHOOK_URL', 'https://eljurkgi.great-site.net/telegram_bot.php');
?>
