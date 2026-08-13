<?php
/**
 * Plugin Name: D&D Character Registry
 * Description: Displays a D&D form and securely relays submissions to the Python API.
 * Version: 1.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

function dnd_registry_render_form()
{
    wp_enqueue_style(
        'dnd-registry-form',
        plugin_dir_url(__FILE__) . 'assets/form.css',
        array(),
        '1.0.0'
    );

    wp_enqueue_script(
        'dnd-registry-form',
        plugin_dir_url(__FILE__) . 'assets/form.js',
        array(),
        '1.0.0',
        true
    );

    wp_localize_script(
        'dnd-registry-form',
        'dndRegistryConfig',
        array('endpoint' => rest_url('dnd-registry/v1/characters'))
    );

    ob_start();
    include plugin_dir_path(__FILE__) . 'templates/form.php';
    return ob_get_clean();
}
add_shortcode('dnd_character_registry', 'dnd_registry_render_form');

function dnd_registry_register_routes()
{
    register_rest_route(
        'dnd-registry/v1',
        '/characters',
        array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => 'dnd_registry_submit_character',
            'permission_callback' => '__return_true',
        )
    );
}
add_action('rest_api_init', 'dnd_registry_register_routes');

function dnd_registry_setting($name)
{
    $environment_value = getenv($name);
    if ($environment_value !== false && $environment_value !== '') {
        return $environment_value;
    }

    return defined($name) ? constant($name) : '';
}

function dnd_registry_submit_character(WP_REST_Request $request)
{
    $api_url = dnd_registry_setting('DND_CLOUD_RUN_URL');
    $integration_secret = dnd_registry_setting('DND_INTEGRATION_SECRET');

    if ($api_url === '' || $integration_secret === '') {
        return new WP_Error(
            'dnd_not_configured',
            'The character registry integration is not configured.',
            array('status' => 500)
        );
    }

    $input = $request->get_json_params();
    $payload = array(
        'name'            => sanitize_text_field($input['name'] ?? ''),
        'character_class' => sanitize_text_field($input['character_class'] ?? ''),
        'level'           => absint($input['level'] ?? 0),
        'alignment'       => sanitize_text_field($input['alignment'] ?? ''),
        'notes'           => sanitize_textarea_field($input['notes'] ?? ''),
    );

    if (
        $payload['name'] === '' ||
        $payload['character_class'] === '' ||
        $payload['alignment'] === '' ||
        $payload['level'] < 1 ||
        $payload['level'] > 20
    ) {
        return new WP_Error(
            'dnd_invalid_character',
            'Please provide valid character details.',
            array('status' => 422)
        );
    }

    $response = wp_remote_post(
        rtrim($api_url, '/') . '/api/characters',
        array(
            'timeout' => 15,
            'headers' => array(
                'Content-Type'         => 'application/json',
                'X-Integration-Secret' => $integration_secret,
            ),
            'body' => wp_json_encode($payload),
        )
    );

    if (is_wp_error($response)) {
        return new WP_Error(
            'dnd_api_unavailable',
            'The guild ledger is temporarily unavailable.',
            array('status' => 502)
        );
    }

    $status = wp_remote_retrieve_response_code($response);
    $body = json_decode(wp_remote_retrieve_body($response), true);

    if ($status < 200 || $status >= 300) {
        return new WP_Error(
            'dnd_api_error',
            $body['detail'] ?? 'The character could not be registered.',
            array('status' => $status)
        );
    }

    return rest_ensure_response($body);
}
