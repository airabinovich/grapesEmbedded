create database grapesEmbedded;

use grapesEmbedded;

create table campos(
    idCampo int unsigned not null auto_increment,
    uuid varchar(50) not null unique,
    primary key(idCampo)
    );

create table sensores(
    idSensor int unsigned not null auto_increment,
    idCampo int unsigned not null,
    address varchar(50) not null unique,
    gpsLat float,
    gpsLong float,
    primary key(idSensor),
    foreign key(idCampo) references campos(idCampo)
    );

create table magnitudes(
    idMagnitud int unsigned not null auto_increment,
    unidad varchar(5) not null,
    nombre varchar(20) not null unique,
    primary key(idMagnitud)
    );

create table mediciones(
    idMedicion int unsigned not null auto_increment,
    fecha datetime not null,
    valor int not null,
    idMagnitud int unsigned not null,
    idSensor int unsigned not null,
    primary key(idMedicion),
    foreign key(idMagnitud) references magnitudes(idMagnitud),
    foreign key(idSensor) references sensores(idSensor)
    );
