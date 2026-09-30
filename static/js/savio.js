// SAVIO - JS applicatif
(function ($) {
    'use strict';

    $(function () {
        // Confirmation générique pour les formulaires de suppression
        $(document).on('submit', 'form[data-confirm]', function (e) {
            var msg = $(this).data('confirm') || 'Confirmer cette action ?';
            if (!window.confirm(msg)) {
                e.preventDefault();
            }
        });

        // Rendre les lignes cliquables (attribut data-href)
        $(document).on('click', 'tr.clickable-row', function (e) {
            if ($(e.target).closest('a, button, form, input, select, textarea').length) return;
            var url = $(this).data('href');
            if (url) window.location = url;
        });

        // Auto-dismiss alerts après 5s
        $('.alert-dismissible.auto-dismiss').each(function () {
            var el = this;
            setTimeout(function () {
                var alert = bootstrap.Alert.getOrCreateInstance(el);
                if (alert) alert.close();
            }, 5000);
        });

        // ----------------------------------------------------------------
        // Sélection en masse (clients / techniciens / etc.)
        // ----------------------------------------------------------------
        function refreshBulkState() {
            var $rows = $('.bulk-select-row');
            if (!$rows.length) return;
            var $checked = $rows.filter(':checked');
            var count = $checked.length;
            $('.js-bulk-count').text(count);
            $('#bulkDeleteBtn').prop('disabled', count === 0);

            // État du « tout sélectionner »
            var $all = $('.bulk-select-all');
            if ($all.length) {
                if (count === 0) {
                    $all.prop('indeterminate', false).prop('checked', false);
                } else if (count === $rows.length) {
                    $all.prop('indeterminate', false).prop('checked', true);
                } else {
                    $all.prop('indeterminate', true).prop('checked', false);
                }
            }
        }

        // Empêcher la propagation du clic sur la ligne cliquable
        $(document).on('click', '.bulk-select-row, .bulk-select-all', function (e) {
            e.stopPropagation();
        });

        $(document).on('change', '.bulk-select-all', function () {
            var checked = $(this).prop('checked');
            $('.bulk-select-row').prop('checked', checked);
            refreshBulkState();
        });

        $(document).on('change', '.bulk-select-row', function () {
            refreshBulkState();
        });

        // Initialisation au chargement
        refreshBulkState();
    });
})(jQuery);
