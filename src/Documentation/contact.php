<?php

require 'PHPMailer-master/src/Exception.php';
require 'PHPMailer-master/src/PHPMailer.php';
require 'PHPMailer-master/src/SMTP.php';

require_once( "/home/wrw/PHP/birdland.php" );

// Validation done in calling client

$name = $_POST['name'];
$email_from = $_POST['email'];            
$comments = $_POST['comments'];            

$mail = new PHPMailer\PHPMailer\PHPMailer();

// $mail->SMTPDebug = 3;                               // Enable verbose debug output

$mail->isSMTP();                                      // Set mailer to use SMTP
$mail->Host = 'mail.messagingengine.com';             // Specify main and backup SMTP servers
$mail->SMTPAuth = true;                               // Enable SMTP authentication
$mail->Username = $birdland_Username;                 // SMTP username
$mail->Password = $birdland_Password;                 // SMTP password
$mail->SMTPSecure = 'tls';                            // Enable TLS encryption, `ssl` also accepted
$mail->Port = 587;                                    // TCP port to connect to

$mail->setFrom( $email_from, 'Birdland User');
$mail->addAddress( $birdland_addAddress, 'Birdland Admin');     // Add a recipient

$mail->isHTML(true);                                  // Set email format to HTML

$message = "";
$message .= "<table>";
$message .= "<tr>";
$message .= "<td>Name</td><td>$name</td>";
$message .= "</tr>";
$message .= "<tr>";
$message .= "<td>Email</td><td>$email_from</td>";
$message .= "</tr>";
$message .= "</table>";

$message .= "<pre>";
$message .= $comments;
$message .= "</pre>";

$message_plain = "";
$message_plain .= "Name: $name\n";
$message_plain .= "Email: $email_from\n";
$message_plain .= "\n";

$message_plain .= $comments;

$mail->Subject = "Contact: $name";
$mail->Body    = $message;
$mail->AltBody = $message_plain;

if(!$mail->send()) {
    $text = '';
    $error = "Send message failed. Error: {$mail->ErrorInfo}";
} else {
    $text = "Message sent. Thank you for contacting us.";
    $error = "";
}

$ret = [ 'text' => $text, 'error' => $error ];
echo json_encode( $ret );

?>   
