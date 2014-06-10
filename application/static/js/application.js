'use strict';

angular.module('sse', [])
    .value('SSEClient', new EventSource('/events'))
    .factory('SSEService', ['SSEClient', '$rootScope', function(SSEClient, $rootScope) {
        return {
            on: function(event, callback) {
                SSEClient.addEventListener(event, function(e) {
                    $rootScope.$apply(callback(e))
                })
            }
        }
    }])
    .value('SSEStatus', { open: false, closed: false })

    .controller('SSEMessages', ['$scope', 'SSEClient', 'SSEStatus', 'SSEService', function($scope, SSEClient, SSEStatus, SSEService) {
        // Controla una lista de mensajes que se reciben por SSE
        $scope.messages = [];

        SSEService.on('message', function(event) {
            var message = JSON.parse(event.data);
            $scope.messages.unshift(message);
        })

        SSEClient.addEventListener('open', function(event) {
            angular.extend(SSEStatus, {open: true});
        }, true);

        SSEClient.addEventListener('close', function(event) {
            angular.extend(SSEStatus, {closed: true});
        }, true);
    }])

    .controller('PostMessage', ['$scope', '$http', function($scope, $http) {
        // Este controlador se encarga de enviar un mensaje del usuario al servidor.
        $scope.userId = Math.floor(Math.random() * 8) + 1;
        $scope.message = '';

        $scope.save = function() {
            var $postPromise = $http({
                url: '/post',
                method: "POST",
                data: JSON.stringify({from: $scope.userId, message: $scope.message}),
                headers: {'Content-Type': 'application/json'}
            });
        };
    }])

;