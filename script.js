let center = [58.59492284542897,49.61446748974598];

function init() {
	let map = new ymaps.Map('map', {
		center: center,
		zoom: 17
	});
}

ymaps.ready(init);